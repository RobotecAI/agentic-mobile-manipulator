import argparse
import copy
import math
import random
import uuid
from typing import Dict, List, Optional, Sequence, Tuple, cast

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

from scripts.slots import Slot, SlotsCollection


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
        """Retrieve the pose of an entity in a specified frame"""
        entity_state = self.connector.call_service(
            ROS2Message(payload={"entity": entity_name}),
            target="/get_entity_state",
            msg_type="simulation_interfaces/srv/GetEntityState",
            timeout_sec=3.0,
        ).payload
        entity_state = cast(GetEntityState.Response, entity_state).state
        return do_transform_pose(
            entity_state.pose,
            self.connector.get_transform(frame, "odom"),
        )

    def get_slot_pose(self, slot_name: str, frame: str = "odom"):
        if frame != "odom":
            raise NotImplementedError("Only odom frame is supported")
        return self.slots[slot_name].origin_pose

    def get_gripping_point(self, unique_object_name: str):
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
            simulation_name = self.spawn_on_spot(
                slot, object_name, item, std_xy, std_yaw
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
        # and thats how it will be distinguished
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
        for entity in tqdm(
            entities.entities, desc="Deleting entities", total=len(entities.entities)
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
        """Calculate the height of an object's gripping point based on its base"""
        object_pose = self.get_pose(object_name)
        # gripping_point_pose = self.get_pose(f"{object_name}_GrippingPoint")
        gripping_point_pose = self.get_gripping_point(object_name)

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

    def find_entity_slot(self, entity_name: str) -> Optional[Slot]:
        """Find the slot that contains the given entity"""
        entity_pose = self.get_pose(entity_name)
        for _, collection in self.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                if slot.is_entity_within_slot(entity_pose=entity_pose):
                    return slot

    def find_entity_pose(self, entity_name: str) -> Pose:
        """
        Find the slot that contains the given entity based on its position
        If entity is in slot return slot pose else return entity pose
        """
        entity_pose = self.get_pose(entity_name)
        for _, collection in self.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                if slot.is_entity_within_slot(entity_pose=entity_pose):
                    return slot.origin_pose

        return entity_pose

    def assign_entities_to_slots(self, entities: Dict[str, EntityState]):
        """Assign entities to their corresponding slots based on position"""
        assigned_slots = set()

        # First pass: assign entities to slots
        for ent_name, ent in entities.items():
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

    def add_collection(self, collection: SlotsCollection) -> None:
        """Add a slots collection to the warehouse"""
        self.slots_collections[collection.tag] = collection

    def get_collection(self, tag: str) -> Optional[SlotsCollection]:
        """Get a specific collection by tag"""
        return self.slots_collections.get(tag)

    def find_empty_racks(self) -> List[str]:
        """Find all racks that have any empty slots"""
        empty_racks = []
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack" and collection.find_empty_slots():
                empty_racks.append(tag)
        return sorted(empty_racks)

    def find_empty_tables(self) -> List[str]:
        """Find all tables that have any empty slots"""
        empty_tables = []
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "table" and collection.find_empty_slots():
                empty_tables.append(tag)
        return sorted(empty_tables)

    def find_empty_slots_on_racks(self) -> Dict[str, List[str]]:
        """Find all empty slots on any rack"""
        empty_slots_by_rack = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "rack":
                empty_slots = collection.find_empty_slots()
                if empty_slots:
                    empty_slots_by_rack[tag] = empty_slots
        return empty_slots_by_rack

    def find_empty_slots_on_tables(self) -> Dict[str, List[str]]:
        """Find all empty slots on any table"""
        empty_slots_by_table = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == "table":
                empty_slots = collection.find_empty_slots()
                if empty_slots:
                    empty_slots_by_table[tag] = empty_slots
        return empty_slots_by_table

    def find_empty_slots_on_rack(self, rack_tag: str) -> List[str]:
        """Find all empty slots on a specific rack"""
        collection = self.get_collection(rack_tag)
        if collection and collection.collection_type == "rack":
            return collection.find_empty_slots()
        return []

    def find_empty_slots_on_table(self, table_tag: str) -> List[str]:
        """Find all empty slots on a specific table"""
        collection = self.get_collection(table_tag)
        if collection and collection.collection_type == "table":
            return collection.find_empty_slots()
        return []

    def get_all_empty_slots(self) -> Dict[str, List[str]]:
        """Get all empty slots across all collections"""
        all_empty_slots = {}
        for tag, collection in self.slots_collections.items():
            empty_slots = collection.find_empty_slots()
            if empty_slots:
                all_empty_slots[tag] = empty_slots
        return all_empty_slots

    def get_collections_by_type(
        self, collection_type: str
    ) -> Dict[str, SlotsCollection]:
        """Get all collections of a specific type"""
        filtered_collections = {}
        for tag, collection in self.slots_collections.items():
            if collection.collection_type == collection_type.lower():
                filtered_collections[tag] = collection
        return filtered_collections

    def get_warehouse_summary(self) -> Dict[str, Dict[str, int]]:
        """Get usage summary for all collections"""
        summary = {}
        for tag, collection in self.slots_collections.items():
            summary[tag] = collection.get_usage_summary()
        return summary

    def get_type_summary(self) -> Dict[str, Dict[str, int]]:
        """Get usage summary grouped by collection type"""
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
        """Get all slots from all collections in a flat dictionary (similar to flat_slots)"""
        all_slots = {}
        for collection in self.slots_collections.values():
            all_slots.update(collection.slots)
        return all_slots

    def get_warehouse_layout_description(self) -> str:
        """Return a formatted description of the warehouse layout with coordinates"""
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
        """Return a formatted description of the warehouse collections names (tables and racks)"""

        collections_by_type = self.get_collections_sorted_by_type()
        lines = ["COLLECTIONS IN THE WAREHOUSE:\n"]
        for col_type, collections in collections_by_type.items():
            if col_type == "garbage_bin":
                continue

            else:
                lines.append(f"{col_type.upper()} COLLECTIONS:")
                for coll in collections:
                    if coll.item_type:
                        lines.append(
                            f"name: {coll.tag}, type of items stored: {coll.item_type}"
                        )
                    else:
                        lines.append(f"name: {coll.tag}")
        return "\n".join(lines)

    def quaternion_to_forward_vector(
        self, q: Quaternion, forward_axis="x"
    ) -> np.ndarray:
        """Convert quaternion to forward vector.

        Args:
            q: Quaternion orientation
            forward_axis: Which axis is forward ('x', 'y', or 'z')
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

    def find_nearest_object_in_fov(
        self,
        camera_pose: Pose,
        entities_states: Dict[str, EntityState],
        fov_angle_degrees: float = 60.0,
        forward_axis: str = "x",
    ) -> Optional[tuple]:
        """
        Find the nearest object within the camera's field of view.

        Args:
            camera_pose: The pose of the camera
            all_entities_states: Dict of entity name to EntityState objects
            fov_angle_degrees: Field of view cone half-angle in degrees (default 60°)
            forward_axis: Which axis is forward in camera frame ('x', 'y', or 'z')

        Returns:
            Tuple of (object_name, object_pose) for nearest object in FOV, or None
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

        nearest_name = None
        nearest_pose = None
        nearest_distance = float("inf")

        for obj_name, entity_state in entities_states.items():
            obj_pose = entity_state.pose

            # Object position
            obj_pos = np.array(
                [obj_pose.position.x, obj_pose.position.y, obj_pose.position.z]
            )

            # Vector from camera to object
            to_object = obj_pos - cam_pos
            distance = np.linalg.norm(to_object)

            # Skip if too close to camera
            if distance < 1e-6:
                continue

            # Check if object is within FOV cone
            to_object_normalized = to_object / distance
            dot_product = np.dot(cam_forward, to_object_normalized)

            if dot_product > cos_fov:  # Object is within FOV
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_pose = obj_pose
                    nearest_name = obj_name

        if nearest_name is not None:
            return (nearest_name, nearest_pose)
        return None

    def get_trash_pose(self, trash_notice_pose: Pose) -> Tuple[str, Pose]:
        """Returns the nearest trash object (name , pose) in the fov of the robot"""
        all_entities_states = self.get_entities(name_filter="cardboardbox03_v02O")
        # we want gripping point entities, so filter rest
        if not all_entities_states:
            raise ValueError("No entites in simulation")

        entities_states = {}
        for name, state in all_entities_states.items():
            if "GrippingPoint" in name and "Side" not in name:
                entities_states[name] = state

        trash = self.find_nearest_object_in_fov(
            camera_pose=trash_notice_pose, entities_states=entities_states
        )

        if trash:
            self.logger.info(f"Trash detected: {trash[0]} at pose:{trash[1]}")
            return trash
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
