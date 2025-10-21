import argparse
import copy
import math
import random
import uuid
from enum import Enum
from operator import attrgetter
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, cast

import numpy as np
import pandas as pd
from geometry_msgs.msg import Point, Pose, Quaternion
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_services,
)
from rosidl_runtime_py.convert import message_to_ordereddict
from simulation_interfaces.msg import EntityState
from simulation_interfaces.srv import (
    GetEntities,
    GetEntityState,
    SetEntityState,
    SpawnEntity,
)
from tf2_geometry_msgs import do_transform_pose
from tf_transformations import euler_from_quaternion, quaternion_from_euler
from tqdm import tqdm

from rai_app.environment.slots import Slot, SlotsCollection


class ObjectWithDistance(NamedTuple):
    obj_name: str
    entity_state: EntityState
    distance: float


class Collection(Enum):
    RETURNED_PACKAGES_TABLE = "t1"
    OUTBOUND_SHIPMENT_TABLE = "t2"
    INSPECTION_TABLE = "t4"
    FREE = "t3"


class SceneManager:
    def __init__(
        self,
        slots_file: str,
        spawnables_file: str,
        connector: ROS2Connector | None = None,
    ):
        self.client = None
        self.object_names = []
        self.object_poses = []
        self.object_orientations = []

        if connector is None:
            self.connector = ROS2Connector(
                executor_type="single_threaded", node_name="scene_manager"
            )
        else:
            self.connector = connector

        self.client = self.connector.node.create_client(SpawnEntity, "spawn_entity")
        self.logger = self.connector.node.get_logger()

        # flat slots for faster access
        self.slots: Dict[str, Slot] = {}
        # collections for group retrieval
        self.slots_collections: Dict[str, SlotsCollection] = {}

        df = pd.read_csv(slots_file, delimiter=",")
        names = df["slot_name"].tolist()
        positions = df[["x", "y", "z"]].values
        quaternions = df[["qx", "qy", "qz", "qw"]].values
        for slot_name, position, quaternion in zip(names, positions, quaternions):
            pose = Pose(
                position=Point(x=position[0], y=position[1], z=position[2]),
                orientation=Quaternion(
                    x=quaternion[0], y=quaternion[1], z=quaternion[2], w=quaternion[3]
                ),
            )

            # Parse collection and slot info from slot_name
            collection_name, slot_tag = slot_name.split("/", 1)
            slot = Slot(tag=slot_name, origin_pose=pose)

            if "garbagecontainer" in slot_name.lower():
                collection_type = "garbage_bin"
            elif "rack" in slot_name.lower():
                collection_type = "rack"
            # NOTE(jmatejcz) checking if name has 't' is not the most reliable way
            # but works for now when there is no items in 'other' collection
            elif "table" in slot_name.lower() or "t" in collection_name:
                collection_type = "table"
            else:
                collection_type = "other"

            self.slots[slot_name] = slot
            if collection_name not in self.slots_collections:
                slot_collection = SlotsCollection(
                    tag=collection_name, collection_type=collection_type
                )
                slot_collection.add_slot(slot)
                self.slots_collections[collection_name] = slot_collection
            else:
                self.slots_collections[collection_name].add_slot(slot)

        self.spawnable_to_uri: dict[str, str] = {}
        df = pd.read_csv(spawnables_file, delimiter=",")
        names = df["object_name"].tolist()
        uris = df["uri"].tolist()
        for name, uri in zip(names, uris):
            self.spawnable_to_uri[name] = uri

    def get_pose(self, entity_name, frame="odom"):
        """Retrieve an entity pose expressed in the requested frame.

        Parameters
        ----------
        entity_name : str
            Name of the simulated entity.
        frame : str, optional
            Target coordinate frame for the pose. Defaults to ``"odom"``.

        Returns
        -------
        Pose | None
            Pose transformed into ``frame`` if available, otherwise ``None`` when
            repeated transform requests fail.
        """
        entity_state = self.connector.call_service(
            ROS2Message(payload={"entity": entity_name}),
            target="/get_entity_state",
            msg_type="simulation_interfaces/srv/GetEntityState",
            timeout_sec=3.0,
        ).payload
        for _ in range(3):
            try:
                entity_state = cast(GetEntityState.Response, entity_state).state
                return do_transform_pose(
                    entity_state.pose,
                    self.connector.get_transform(frame, "odom"),
                )
            except Exception as e:
                self.logger.error(f"Failed to get pose for {entity_name}: {e}")
                continue

    def get_slot_pose(self, slot_name: str, frame: str = "odom"):
        if frame != "odom":
            raise NotImplementedError("Only odom frame is supported")
        return self.slots[slot_name].origin_pose

    def get_top_gripping_point(self, unique_object_name: str):
        entity_state = GetEntityState.Request()
        entity_state.entity = unique_object_name + "_GrippingPoint"
        pose = self.get_pose(entity_state.entity)
        return pose

    def populate_scene(
        self,
        slots: list[str],
        object_names: list[str],
        items_stored: Optional[Sequence[None | str]] = None,
        std_xy: float = 0.0,
        std_yaw: float = 0.0,
        percent_of_rotated_objects: float = 0.0,
    ):
        if items_stored is None:
            items_stored = [None] * len(object_names)

        if len(slots) != len(object_names) != len(items_stored):
            raise ValueError(
                "Slots and object names must have the same length and items stored"
            )

        # TODO(maciejmajek): This line freezes execution
        # self.logger.info(f"Populating scene with {len(slots)} entities")
        simulation_names: list[str] = []
        for slot, object_name, item in tqdm(
            zip(slots, object_names, items_stored),
            desc="Spawning entities",
            total=len(slots),
        ):
            should_rotate = random.random() < percent_of_rotated_objects
            if should_rotate:
                # rotate additional 90 degrees
                additional_rotation = 1.57
            else:
                additional_rotation = 0.0
            simulation_name = self.spawn_on_spot(
                slot,
                object_name,
                item,
                std_xy,
                std_yaw,
                additional_rotation=additional_rotation,
            )
            simulation_names.append(simulation_name)
        return simulation_names

    def spawn_object(
        self,
        pose: Pose,
        object_name: str,
        item_stored: Optional[str] = None,
        frame: str = "odom",
    ):
        wait_for_ros2_services(self.connector, ["/spawn_entity"])
        # NOTE (jmatejcz) item stored will be added to name of object
        # and that's how it will be distinguished
        if item_stored:
            name = object_name + f"__{item_stored}__" + str(uuid.uuid4())[:8]
        else:
            name = object_name + str(uuid.uuid4())[:8]

        req = SpawnEntity.Request()
        req.name = name
        req.uri = self.spawnable_to_uri[object_name]
        req.initial_pose.header.frame_id = frame
        req.initial_pose.pose.position.x = pose.position.x
        req.initial_pose.pose.position.y = pose.position.y
        req.initial_pose.pose.position.z = pose.position.z
        req.initial_pose.pose.orientation.x = pose.orientation.x
        req.initial_pose.pose.orientation.y = pose.orientation.y
        req.initial_pose.pose.orientation.z = pose.orientation.z
        req.initial_pose.pose.orientation.w = pose.orientation.w

        self.logger.debug(f"Spawning {name}")
        result = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req)),
            target="/spawn_entity",
            msg_type="simulation_interfaces/srv/SpawnEntity",
            timeout_sec=3.0,
            reuse_client=True,
        ).payload
        result = cast(SpawnEntity.Response, result)
        return name

    def spawn_on_spot(
        self,
        slot_name: str,
        object_name: str,
        item_stored: Optional[str] = None,
        std_xy: float = 0.0,
        std_yaw: float = 0.0,
        frame: str = "odom",
        additional_rotation: float = 0.0,
    ):
        wait_for_ros2_services(self.connector, ["/spawn_entity"])
        pose: Pose = copy.deepcopy(self.slots[slot_name].origin_pose)
        # Add Gaussian noise to x, y
        pose.position.x += random.normalvariate(0, std_xy)
        pose.position.y += random.normalvariate(0, std_xy)

        # Convert quaternion -> Euler
        q = pose.orientation
        roll, pitch, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # Add Gaussian noise to yaw
        yaw += random.normalvariate(0, std_yaw)
        yaw += additional_rotation

        # Convert back to quaternion
        q_new = quaternion_from_euler(roll, pitch, yaw)
        pose.orientation.x = q_new[0]
        pose.orientation.y = q_new[1]
        pose.orientation.z = q_new[2]
        pose.orientation.w = q_new[3]

        return self.spawn_object(
            pose=pose, object_name=object_name, item_stored=item_stored, frame=frame
        )

    def clear_scene(self):
        # TODO(maciejmajek): This line freezes the execution
        # self.logger.info("Clearing spawnable entities")
        wait_for_ros2_services(self.connector, ["/get_entities", "/delete_entity"])
        response = self.connector.call_service(
            ROS2Message(payload={}),
            target="/get_entities",
            msg_type="simulation_interfaces/srv/GetEntities",
            timeout_sec=3.0,
        )
        entities = cast(GetEntities.Response, response.payload)

        filtered_entities: list[str] = [
            entity
            for entity in cast(list[str], entities.entities)
            if "grippingpoint" not in entity.lower()
        ]
        for entity in tqdm(
            filtered_entities, desc="Deleting entities", total=len(filtered_entities)
        ):
            self.logger.debug(f"Deleting {entity}")
            self.connector.call_service(
                ROS2Message(payload={"entity": entity}),
                target="/delete_entity",
                msg_type="simulation_interfaces/srv/DeleteEntity",
                timeout_sec=3.0,
            )

    def move_entity(
        self,
        entity_name,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        sx=0.0,
        sy=0.0,
        sz=0.0,
        ax=0.0,
        ay=0.0,
        az=0.0,
    ):
        wait_for_ros2_services(
            self.connector, ["/get_entity_state", "/set_entity_state"]
        )

        req_get = GetEntityState.Request()
        req_get.entity = entity_name
        response = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req_get)),
            target="/get_entity_state",
            msg_type="simulation_interfaces/srv/GetEntityState",
            timeout_sec=3.0,
        ).payload
        entity_state = cast(GetEntityState.Response, response)

        req = SetEntityState.Request()
        req.entity = entity_name  # Entity name in simulation
        req.state.pose.position.x = entity_state.state.pose.position.x + dx
        req.state.pose.position.y = entity_state.state.pose.position.y + dy
        req.state.pose.position.z = entity_state.state.pose.position.z + dz
        req.state.pose.orientation.x = entity_state.state.pose.orientation.x
        req.state.pose.orientation.y = entity_state.state.pose.orientation.y
        req.state.pose.orientation.z = entity_state.state.pose.orientation.z
        req.state.pose.orientation.w = entity_state.state.pose.orientation.w
        req.state.twist.linear.x = sx
        req.state.twist.linear.y = sy
        req.state.twist.linear.z = sz
        req.state.twist.angular.x = ax
        req.state.twist.angular.y = ay
        req.state.twist.angular.z = az
        req.state.header.frame_id = entity_state.state.header.frame_id

        result = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req)),
            target="/set_entity_state",
            msg_type="simulation_interfaces/srv/SetEntityState",
            timeout_sec=3.0,
        ).payload
        response = cast(SetEntityState.Response, result)

        if response.result is not None:
            if response.result.result == 1:
                print(f"Moved {entity_name}")
            else:
                self.logger.error(
                    f"Failed to move {entity_name}. Error: {response.result.error_message}"
                )
        else:
            raise RuntimeError(f"Failed to move {entity_name}. Error: {response}")

    def get_object_height(self, object_name: str):
        """Compute the vertical offset between the object base and gripping point.

        Parameters
        ----------
        object_name : str
            Identifier of the object whose gripping point height is required.

        Returns
        -------
        float
            Absolute height difference in meters.
        """
        object_pose = self.get_pose(object_name)
        # gripping_point_pose = self.get_pose(f"{object_name}_GrippingPoint")
        gripping_point_pose = self.get_top_gripping_point(object_name)

        return np.abs(gripping_point_pose.position.z - object_pose.position.z)

    def get_entities(self, name_filter: str) -> Optional[Dict[str, EntityState]]:
        response = self.connector.call_service(
            ROS2Message(payload={"filters": {"filter": name_filter}}),
            target="/get_entities_states",
            msg_type="simulation_interfaces/srv/GetEntitiesStates",
            timeout_sec=3.0,
        ).payload

        entities: Dict[str, EntityState] = {}
        if response is not None:
            for i, name in enumerate(response.entities):
                entities[name] = response.states[i]
            return entities

    def filter_out_gripping_point_entites(self, entities: Dict[str, EntityState]):
        filtered_entities = {}
        for name, ent in entities.items():
            if "grippingpoint" not in name.lower():
                filtered_entities[name] = ent

        return filtered_entities

    def find_entity_slot(self, entity_name: str) -> Optional[Slot]:
        """Locate the slot that currently contains a given entity.

        Parameters
        ----------
        entity_name : str
            Name of the entity to search for.

        Returns
        -------
        Slot | None
            Slot containing the entity, or ``None`` if the entity is not inside
            any registered slot.
        """
        entity_pose = self.get_pose(entity_name)
        for _, collection in self.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                if slot.is_entity_within_slot(entity_pose=entity_pose):
                    return slot

    def find_entity_pose(self, entity_name: str) -> Pose:
        """Return the slot pose if the entity resides in a slot, otherwise entity pose.

        Parameters
        ----------
        entity_name : str
            Name of the entity whose pose is required.

        Returns
        -------
        Pose
            Slot origin pose when the entity occupies a slot, or the raw entity
            pose if not.
        """
        entity_pose = self.get_pose(entity_name)
        for _, collection in self.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                if slot.is_entity_within_slot(entity_pose=entity_pose):
                    return slot.origin_pose

        return entity_pose

    def assign_entities_to_slots(self, entities: Dict[str, EntityState]):
        """Assign simulated entities to slots based on spatial inclusion.

        Parameters
        ----------
        entities : dict[str, EntityState]
            Mapping between entity names and their simulation states.
        """
        assigned_slots = set()

        filtered_entities = self.filter_out_gripping_point_entites(entities=entities)

        # First pass: assign entities to slots
        for ent_name, ent in filtered_entities.items():
            for coll_name, collection in self.slots_collections.items():
                for slot_name, slot in collection.slots.items():
                    if slot.is_entity_within_slot(entity_pose=ent.pose):
                        slot.assign_entity_to_slot(name=ent_name)
                        assigned_slots.add((coll_name, slot_name))

        # Second pass: remove entities from slots that weren't assigned
        for coll_name, collection in self.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                if (coll_name, slot_name) not in assigned_slots:
                    slot.remove_entity_from_slot()

    def assign_collections_to_item_types(
        self, collections_names: List[str], item_types: List[str]
    ):
        for coll_name, item_type in zip(collections_names, item_types):
            self.slots_collections[coll_name].item_type = item_type

    def get_object_type_to_racks(self, object_type: str) -> List[str]:
        """Get all racks that typically store a specific object type.

        Parameters
        ----------
        object_type : str
            Type of object to search for (e.g., "cpu", "gpu", "pipes")

        Returns
        -------
        list[str]
            List of rack identifiers that store this object type
        """
        object_type_to_racks: Dict[str, List[str]] = {}

        # Build mapping from collections that are racks
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack":
                # Check if this rack has an assigned item type
                if hasattr(collection, "item_type") and collection.item_type:
                    if collection.item_type not in object_type_to_racks:
                        object_type_to_racks[collection.item_type] = []
                    object_type_to_racks[collection.item_type].append(tag)

        return object_type_to_racks.get(object_type, [])

    def get_object_type_to_racks_all(self) -> Dict[str, List[str]]:
        """Get complete mapping of all object types to their storage racks.

        Returns
        -------
        dict[str, list[str]]
            Mapping of object types to lists of rack identifiers
        """
        object_type_to_racks: Dict[str, List[str]] = {}

        # Build complete mapping from rack collections
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack":
                # Check if this rack has an assigned item type
                if hasattr(collection, "item_type") and collection.item_type:
                    if collection.item_type not in object_type_to_racks:
                        object_type_to_racks[collection.item_type] = []
                    object_type_to_racks[collection.item_type].append(tag)

        # Sort rack lists for consistent output
        for racks in object_type_to_racks.values():
            racks.sort()

        return object_type_to_racks

    def add_collection(self, collection: SlotsCollection) -> None:
        """Register a slots collection within the warehouse scene graph.

        Parameters
        ----------
        collection : SlotsCollection
            Collection instance to insert.
        """
        self.slots_collections[collection.tag] = collection

    def get_collection(self, tag: str) -> Optional[SlotsCollection]:
        """Retrieve a collection by its identifier.

        Parameters
        ----------
        tag : str
            Collection identifier.

        Returns
        -------
        SlotsCollection | None
            Collection instance when present, otherwise ``None``.
        """
        return self.slots_collections.get(tag)

    def find_empty_racks(self) -> List[str]:
        """Return rack identifiers containing at least one empty slot.

        Returns
        -------
        list[str]
            Sorted list of rack identifiers with available capacity.
        """
        empty_racks = []
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack" and collection.find_empty_slots():
                empty_racks.append(tag)
        return sorted(empty_racks)

    def find_empty_tables(self) -> List[str]:
        """Return table identifiers containing at least one empty slot.

        Returns
        -------
        list[str]
            Sorted list of table identifiers with available capacity.
        """
        empty_tables = []
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "table" and collection.find_empty_slots():
                empty_tables.append(tag)
        return sorted(empty_tables)

    def find_empty_slots_on_racks(self) -> Dict[str, List[str]]:
        """List empty slots grouped by rack identifier.

        Returns
        -------
        dict[str, list[str]]
            Mapping of rack identifiers to lists of empty slot tags.
        """
        empty_slots_by_rack = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack":
                empty_slots = collection.find_empty_slots()
                if empty_slots:
                    empty_slots_by_rack[tag] = empty_slots
        return empty_slots_by_rack

    def find_empty_slots_on_tables(self) -> Dict[str, List[str]]:
        """List empty slots grouped by table identifier.

        Returns
        -------
        dict[str, list[str]]
            Mapping of table identifiers to lists of empty slot tags.
        """
        empty_slots_by_table = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "table":
                empty_slots = collection.find_empty_slots()
                if empty_slots:
                    empty_slots_by_table[tag] = empty_slots
        return empty_slots_by_table

    def find_empty_slots_on_rack(self, rack_tag: str) -> List[str]:
        """Return empty slot tags for a specific rack.

        Parameters
        ----------
        rack_tag : str
            Rack identifier.

        Returns
        -------
        list[str]
            Empty slot tags; empty list when no slots are free.
        """
        collection = self.get_collection(rack_tag)
        if collection and collection.collection_type == "rack":
            return collection.find_empty_slots()
        return []

    def find_empty_slots_on_table(self, table_tag: str) -> List[str]:
        """Return empty slot tags for a specific table.

        Parameters
        ----------
        table_tag : str
            Table identifier.

        Returns
        -------
        list[str]
            Empty slot tags; empty list when no slots are free.
        """
        collection = self.get_collection(table_tag)
        if collection and collection.collection_type == "table":
            return collection.find_empty_slots()
        return []

    def get_all_empty_slots(self) -> Dict[str, List[str]]:
        """Return a mapping of all collections to their empty slots.

        Returns
        -------
        dict[str, list[str]]
            Collections keyed by identifier with lists of empty slot tags.
        """
        all_empty_slots = {}
        for tag, collection in self.slots_collections.items():
            empty_slots = collection.find_empty_slots()
            if empty_slots:
                all_empty_slots[tag] = empty_slots
        return all_empty_slots

    def get_collections_by_type(
        self, collection_type: str
    ) -> Dict[str, SlotsCollection]:
        """Retrieve all collections matching a specific type.

        Parameters
        ----------
        collection_type : str
            Collection type label (for example ``"rack"`` or ``"table"``).

        Returns
        -------
        dict[str, SlotsCollection]
            Collections filtered by type.
        """
        filtered_collections = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == collection_type.lower():
                filtered_collections[tag] = collection
        return filtered_collections

    def get_warehouse_summary(self) -> Dict[str, Dict[str, int]]:
        """Summarize slot usage metrics per collection.

        Returns
        -------
        dict[str, dict[str, int]]
            Mapping of collection tags to usage counts (total, used, free).
        """
        summary = {}
        for tag, collection in self.slots_collections.items():
            summary[tag] = collection.get_usage_summary()
        return summary

    def get_type_summary(self) -> Dict[str, Dict[str, int]]:
        """Summarize slot usage metrics grouped by collection type.

        Returns
        -------
        dict[str, dict[str, int]]
            Usage counts aggregated by collection type.
        """
        type_summary = {}

        for collection in self.slots_collections.values():
            col_type = collection.collection_type or "unknown"
            if col_type not in type_summary:
                type_summary[col_type] = {"total": 0, "used": 0, "free": 0}

            usage = collection.get_usage_summary()
            type_summary[col_type]["total"] += usage["total"]
            type_summary[col_type]["used"] += usage["used"]
            type_summary[col_type]["free"] += usage["free"]

        return type_summary

    def get_collections_sorted_by_type(self) -> Dict[str, List[SlotsCollection]]:
        collections_by_type: Dict[str, List[SlotsCollection]] = {}
        for tag, collection in self.slots_collections.items():
            col_type = collection.collection_type
            if col_type not in collections_by_type:
                collections_by_type[col_type] = []
            collections_by_type[col_type].append(collection)

        return collections_by_type

    def get_all_slots(self) -> Dict[str, Slot]:
        """Return a flat dictionary of all slots across collections.

        Returns
        -------
        dict[str, Slot]
            Mapping of slot tag to slot instance.
        """
        all_slots = {}
        for collection in self.slots_collections.values():
            all_slots.update(collection.slots)
        return all_slots

    def get_warehouse_layout_description(self) -> str:
        """Build a human-readable description of the warehouse layout.

        Returns
        -------
        str
            Multi-line string containing collection and slot occupancy details.
        """
        lines = ["CURRENT WAREHOUSE LAYOUT:\n"]
        collections_by_type = self.get_collections_sorted_by_type()
        # Sort types for consistent output
        for collection_type in sorted(collections_by_type.keys()):
            collections = collections_by_type[collection_type]
            # Sort collections by tag
            collections.sort(key=lambda x: x[0])

            for collection in collections:
                # Add collection header
                lines.append(
                    f"{collection_type} {collection.collection_type} with slots:\n"
                )

                # Sort slots by tag for consistent output
                sorted_slots = sorted(collection.slots.items())

                for slot_tag, slot in sorted_slots:
                    if slot.is_obj_present():
                        obj_name = slot.get_obj_name()
                        status = f"occupied by {obj_name}"
                    else:
                        status = "empty"

                    lines.append(f"    {slot_tag} - {status}")

        return "\n".join(lines)

    def get_warehouse_collections_description(self) -> str:
        """Summarize the default storage collections by object type.

        Returns
        -------
        str
            Multi-line string describing which collections store each object type.
        """

        object_type_to_racks = self.get_object_type_to_racks_all()
        lines = [
            "There are several racks in the in the warehouse and following objects are stored in them:"
        ]
        for object_type, racks in object_type_to_racks.items():
            lines.append(f"- racks: {racks} - they usually store {object_type}")
        return "\n".join(lines)

    def quaternion_to_forward_vector(
        self, q: Quaternion, forward_axis="x"
    ) -> np.ndarray:
        """Convert a quaternion orientation to a forward vector.

        Parameters
        ----------
        q : Quaternion
            Orientation to convert.
        forward_axis : str, optional
            Axis treated as the forward direction (``"x"``, ``"y"``, or ``"z"``).
            Defaults to ``"x"``.

        Returns
        -------
        numpy.ndarray
            Unit vector representing the forward direction.
        """
        x, y, z, w = q.x, q.y, q.z, q.w

        if forward_axis == "x":
            # X-axis forward (common in 2D navigation)
            forward = np.array(
                [1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y)]
            )
        elif forward_axis == "y":
            # Y-axis forward
            forward = np.array(
                [2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x)]
            )
        else:  # 'z'
            # Z-axis forward (3D cameras looking down/up)
            forward = np.array(
                [2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)]
            )

        return forward / np.linalg.norm(forward)

    def _get_objects_in_fov_with_distances(
        self,
        camera_pose: Pose,
        entities_states: Dict[str, EntityState],
        fov_angle_degrees: float = 60.0,
        forward_axis: str = "x",
    ) -> Optional[list[ObjectWithDistance]]:
        """Return objects inside the field of view annotated with distance.

        Parameters
        ----------
        camera_pose : Pose
            Camera pose expressed in the world frame.
        entities_states : dict[str, EntityState]
            Mapping of entity names to simulation states.
        fov_angle_degrees : float, optional
            Field of view angle in degrees. Defaults to ``60.0``.
        forward_axis : str, optional
            Axis describing the camera forward direction. Defaults to ``"x"``.

        Returns
        -------
        list[ObjectWithDistance] | None
            Objects within the FOV sorted by distance, or ``None`` when no
            entities are visible.
        """
        if not entities_states:
            return None

        cam_pos = np.array(
            [camera_pose.position.x, camera_pose.position.y, camera_pose.position.z]
        )
        cam_forward = self.quaternion_to_forward_vector(
            camera_pose.orientation, forward_axis
        )

        # FOV threshold
        cos_fov = math.cos(math.radians(fov_angle_degrees))

        filtered_objects: list[ObjectWithDistance] = []

        for obj_name, entity_state in entities_states.items():
            obj_pose = entity_state.pose

            # Object position
            obj_pos = np.array(
                [obj_pose.position.x, obj_pose.position.y, obj_pose.position.z]
            )

            # Vector from camera to object
            to_object = obj_pos - cam_pos
            distance = float(np.linalg.norm(to_object))

            # Skip if too close to camera
            if distance < 1e-6:
                continue

            # Check if object is within FOV cone
            to_object_normalized = to_object / distance
            dot_product = np.dot(cam_forward, to_object_normalized)

            if dot_product > cos_fov:  # Object is within FOV
                filtered_objects.append(
                    ObjectWithDistance(obj_name, entity_state, distance)
                )
        return filtered_objects

    def find_nearest_out_of_slot_in_fov(
        self,
        camera_pose: Pose,
        entities_states: Dict[str, EntityState],
        fov_angle_degrees: float = 60.0,
        forward_axis: str = "x",
        filter_poses: Optional[list[Pose]] = None,
    ) -> Optional[Tuple[str, EntityState]]:
        """Return the closest object outside a slot within the camera FOV.

        Parameters
        ----------
        camera_pose : Pose
            Camera pose in the world frame.
        entities_states : dict[str, EntityState]
            Mapping of entity names to states.
        fov_angle_degrees : float, optional
            Field of view angle in degrees. Defaults to ``60.0``.
        forward_axis : str, optional
            Camera forward axis. Defaults to ``"x"``.
        filter_poses : list[Pose], optional
            Poses to exclude from consideration.

        Returns
        -------
        tuple[str, EntityState] | None
            Entity name and state when a candidate is found; otherwise ``None``.
        """
        objects_in_fov = self._get_objects_in_fov_with_distances(
            camera_pose, entities_states, fov_angle_degrees, forward_axis
        )
        if objects_in_fov is None:
            return None
        if filter_poses is None:
            filter_poses = []
        objects_in_fov.sort(key=attrgetter("distance"))

        for o_name, o_state, _ in objects_in_fov:
            if o_state.pose in filter_poses:
                continue
            found_slot_flag = False
            for slot in self.slots.values():
                if slot.is_entity_within_slot(o_state.pose):
                    found_slot_flag = True
            if not found_slot_flag:
                return (o_name, o_state)
        return None

    def find_nearest_object_in_fov(
        self,
        camera_pose: Pose,
        entities_states: Dict[str, EntityState],
        fov_angle_degrees: float = 60.0,
        forward_axis: str = "x",
    ) -> Optional[tuple]:
        """Return the nearest object within the camera field of view.

        Parameters
        ----------
        camera_pose : Pose
            Camera pose expressed in the world frame.
        entities_states : dict[str, EntityState]
            Mapping of entity names to states.
        fov_angle_degrees : float, optional
            Field of view angle. Defaults to ``60.0``.
        forward_axis : str, optional
            Axis treated as camera forward direction. Defaults to ``"x"``.

        Returns
        -------
        tuple[str, Pose] | None
            Nearest object name and pose, or ``None`` when no object is visible.
        """
        objects_in_fov = self._get_objects_in_fov_with_distances(
            camera_pose, entities_states, fov_angle_degrees, forward_axis
        )
        if objects_in_fov is None:
            return None

        found = min(objects_in_fov, key=attrgetter("distance"))

        return (found.obj_name, found.entity_state.pose)

    def get_anomaly_box_pose(
        self, trash_notice_pose: Pose, filter_poses: Optional[list[Pose]] = None
    ) -> Tuple[str, Pose]:
        """Find the closest box anomaly visible to the robot.

        Parameters
        ----------
        trash_notice_pose : Pose
            Current robot pose used for visibility computation.
        filter_poses : list[Pose], optional
            List of poses to ignore to avoid duplicate anomalies.

        Returns
        -------
        tuple[str, Pose]
            Entity name and gripping point pose.

        Raises
        ------
        ValueError
            If no box anomalies are detected within the field of view.
        """
        all_entities = self.get_entities(name_filter="cardboardbox")
        # we want gripping point entities, so filter rest
        if not all_entities:
            raise ValueError("No entities in simulation")

        filtered_entities = self.filter_out_gripping_point_entites(
            entities=all_entities
        )

        obj = self.find_nearest_out_of_slot_in_fov(
            camera_pose=trash_notice_pose,
            entities_states=filtered_entities,
            filter_poses=filter_poses,
        )

        if obj:
            trash_name = obj[0]
            trash_gripping_point = self.get_top_gripping_point(trash_name)
            self.logger.debug(
                f"Trash detected: {trash_name} at pose {trash_gripping_point}"
            )
            return trash_name, trash_gripping_point
        else:
            raise ValueError("Trash pose not detected")

    def get_angle_between_points(self, p1, p2, p3) -> float:
        v1 = np.array([p3.x - p2.x, p3.y - p2.y])
        v2 = np.array([p1.x - p2.x, p1.y - p2.y])
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        return angle

    def find_closest_side_gripping_point(
        self, entity_name: str, camera_pose: Pose
    ) -> Pose:
        side_gripping_points = [
            self.get_pose(entity_name + f"_SideGrippingPoint{i}") for i in range(1, 5)
        ]
        object_pose = self.get_pose(entity_name)

        closest_gripping_point = max(
            enumerate(side_gripping_points),
            # find the point with most straight angle to the robot
            key=lambda p: self.get_angle_between_points(
                camera_pose.position, p[1].position, object_pose.position
            ),
        )
        return closest_gripping_point[1]


@ROS2Context()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--spawn", action="store_true", default=True)
    parser.add_argument("--slots-file", type=str, default="scripts/resources/slots.csv")
    parser.add_argument(
        "--spawnables-file", type=str, default="scripts/resources/spawnables.csv"
    )
    parser.add_argument("--filter", type=str, default="ego|oilspill1|oilspill2")
    args = parser.parse_args()

    scene_manager = SceneManager(
        slots_file=args.slots_file, spawnables_file=args.spawnables_file
    )

    slots = pd.read_csv(args.slots_file, delimiter=",")
    spawnables = pd.read_csv(args.spawnables_file, delimiter=",")
    spawnables = spawnables[~spawnables["object_name"].isin(args.filter.split("|"))]

    object_names = [
        random.choice(list(spawnables["object_name"].tolist()))
        for _ in range(len(slots))
    ]

    slot_names = slots["slot_name"].tolist()

    if args.spawn:
        scene_manager.populate_scene(slot_names, object_names)

    if args.clear:
        scene_manager.clear_scene()

    scene_manager.connector.shutdown()


if __name__ == "__main__":
    main()
