# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Developed by Robotec.ai sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import math
from typing import Dict, List, Optional, Tuple

import rclpy
from geometry_msgs.msg import Point, Pose, Quaternion
from simulation_interfaces.msg import EntityState
from simulation_interfaces.srv import GetEntitiesStates


class Slot:
    def __init__(self, tag: str, origin_pose: Pose):
        """Represent a location where an object can be placed or retrieved.

        Parameters
        ----------
        tag : str
            Slot identifier, e.g. ``"J01/RackSlot1"``.
        origin_pose : Pose
            Pose describing the slot origin used for reachability checks.
        """

        self.tag = tag
        self.origin_pose = origin_pose
        self._entity_name: Optional[str] = None

    def is_entity_within_slot(self, entity_pose: Pose):
        slot_x = self.origin_pose.position.x
        slot_y = self.origin_pose.position.y
        slot_z = self.origin_pose.position.z

        entity_x = entity_pose.position.x
        entity_y = entity_pose.position.y
        entity_z = entity_pose.position.z

        z_diff = abs(entity_z - slot_z)
        if z_diff <= 0.05:
            height_match = True
        else:
            height_match = False

        distance = math.sqrt((entity_x - slot_x) ** 2 + (entity_y - slot_y) ** 2)

        return height_match and distance <= 0.15

    def is_manipulation_feasible(self) -> bool:
        """Return ``True`` when the slot can be manipulated by the arm."""
        RACKS_OPPOSING_WALL = [f"L{str(i)}" for i in range(1, 10)]
        SLOTS_FACING_BACKWARD = ["RackSlot" + str(i) for i in range(1, 13)]

        RACKS_FACING_WALL = (
            [f"F{str(i).zfill(2)}" for i in range(1, 10)]
            + [f"A{str(i).zfill(2)}" for i in range(1, 7)]
            + [f"G{str(i).zfill(2)}" for i in range(1, 7)]
        )
        SLOTS_FACING_FORWARD = ["RackSlot" + str(i) for i in range(13, 25)]

        ret = True
        if self.tag.startswith(tuple(RACKS_OPPOSING_WALL)) and self.tag.endswith(
            tuple(SLOTS_FACING_BACKWARD)
        ):
            ret = False
        if self.tag.startswith(tuple(RACKS_FACING_WALL)) and self.tag.endswith(
            tuple(SLOTS_FACING_FORWARD)
        ):
            ret = False

        return ret

    def assign_entity_to_slot(self, name: str):
        self._entity_name = name

    def remove_entity_from_slot(self):
        self._entity_name = None

    def is_obj_present(self) -> bool:
        """Return ``True`` if an object is currently assigned to the slot."""
        if self._entity_name:
            return True
        else:
            return False

    def get_obj_name(self) -> Optional[str]:
        return self._entity_name

    def get_item_stored(self) -> Optional[str]:
        """Return stored item type extracted from the object name, if available."""
        if self._entity_name:
            # NOTE (jmatejcz) assuming '__' is only present in name when item stored
            # in this object
            if "__" in self._entity_name:
                item_stored = self._entity_name.split("__")[1]
                return item_stored.lower()


class SlotsCollection:
    """Logical grouping of related slots (for example tables or racks)."""

    def __init__(self, tag: str, collection_type: str = ""):
        """Initialize a collection of slots.

        Parameters
        ----------
        tag : str
            Identifier for this collection, e.g. ``"table1"``.
        collection_type : str, optional
            Collection type (``"table"``, ``"rack"``, etc.). Defaults to ``""``.
        """
        self.tag = tag
        self.collection_type = collection_type
        self.slots: Dict[str, Slot] = {}
        # item type stored in tis collection
        self.item_type: Optional[str] = None

    def add_slot(self, slot: Slot) -> None:
        """Insert a slot into the collection."""
        self.slots[slot.tag] = slot

    def get_slot(self, tag: str) -> Optional[Slot]:
        """Return a slot by tag when present."""
        return self.slots.get(tag)

    def get_all_slots(self) -> Dict[str, Slot]:
        """Return a shallow copy of all slots in the collection."""
        return self.slots.copy()

    def find_empty_slots(self) -> List[Slot]:
        """Return slots that are empty and reachable for manipulation."""
        empty_slots = []
        for _, slot in self.slots.items():
            if not slot.is_obj_present() and slot.is_manipulation_feasible():
                empty_slots.append(slot)
        return empty_slots

    def find_used_slots(self) -> List[Slot]:
        """Return occupied slots that remain reachable for manipulation."""
        used_slots = []
        for _, slot in self.slots.items():
            if slot.is_obj_present() and slot.is_manipulation_feasible():
                used_slots.append(slot)
        return used_slots

    def get_slot_with_object(self, obj_name: str) -> Optional[Slot]:
        """Return the slot containing the specified object name, if any."""
        for slot in self.slots.values():
            if slot.get_obj_name() == obj_name:
                return slot
        return None

    def find_slots_with_item_type(self, item_type: str) -> List[Slot]:
        """Return slots containing packages with the requested item type."""
        slots_with_item_type = []
        for _, slot in self.slots.items():
            if item_type.lower() == slot.get_item_stored():
                slots_with_item_type.append(slot)
        return slots_with_item_type

    def get_usage_summary(self) -> Dict[str, int]:
        """Return counts of total, used, and free slots in the collection."""
        total_count = len(self.slots)
        used_count = sum(1 for slot in self.slots.values() if slot.is_obj_present())
        free_count = total_count - used_count

        return {
            "total": total_count,
            "used": used_count,
            "free": free_count,
        }

    @property
    def middle_position(self) -> Point:
        """Calculate and return the average position of all slots in this collection"""
        if not self.slots:
            return Point()

        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        count = len(self.slots)

        for slot in self.slots.values():
            total_x += slot.origin_pose.position.x
            total_y += slot.origin_pose.position.y
            total_z += slot.origin_pose.position.z

        return Point(x=total_x / count, y=total_y / count, z=total_z / count)

    def _get_unique_orientations(self) -> List[Quaternion]:
        """
        Extract all unique orientations from slots in the collection.
        """
        if not self.slots:
            return set()

        orientations = set()
        orientations_list: List[Quaternion] = []
        for slot in self.slots.values():
            orient = slot.origin_pose.orientation
            # quaterion is unhasable so use a tuple here
            orient_tuple = (orient.x, orient.y, orient.z, orient.w)
            if orient_tuple not in orientations:
                orientations.add(orient_tuple)
                orientations_list.append(orient)

        return orientations_list

    @property
    def middle_poses(self) -> Tuple[Pose, Pose]:
        """
        Calculate and return two view poses at the middle position facing opposite directions.

        This follows the same logic as view_of_racks_pose for a single rack collection.

        Returns:
            Tuple[Pose, Pose]: Two view poses with the same position but opposite orientations

        Raises:
            ValueError: If slots collection is empty or has invalid orientation
        """
        if not self.slots:
            raise ValueError("Slots collection is empty")

        unique_orientations = self._get_unique_orientations()

        if len(unique_orientations) != 2:
            raise ValueError(
                f"Collection must have exactly 2 unique orientations, found {len(unique_orientations)}"
            )

        avg_position = self.middle_position
        orientations_list = list(unique_orientations)

        # Create first pose with first orientation
        view_pose1 = Pose()
        view_pose1.position = Point(
            x=avg_position.x, y=avg_position.y, z=avg_position.z
        )
        view_pose1.orientation = orientations_list[0]

        # Create second pose with second orientation
        view_pose2 = Pose()
        view_pose2.position = Point(
            x=avg_position.x, y=avg_position.y, z=avg_position.z
        )
        view_pose2.orientation = orientations_list[1]

        return view_pose1, view_pose2

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        summary = self.get_usage_summary()
        return f"{self.tag} ({self.collection_type}): {summary['used']}/{summary['total']} used"


def get_all_slots_from_file(filepath: str) -> Dict[str, SlotsCollection]:
    """Load slot definitions from a CSV file produced by the simulation."""
    # NOTE (jmatejcz) simulation publishes once all slots and their coords to ros topic
    # so it is not possible to get it via python api
    # for now it is stored in file

    # they will be named like table1_spot1, so we will extract collcetion from name
    # sample data:
    # name,      id ?            , x,     y,    z,    qx,   qy,   qz,   qw
    # RackSlot2,[129235007734410],23.737,29.749,0.850,0.000,0.000,0.707,0.707
    slots_collections: Dict[str, SlotsCollection] = {}

    with open(filepath, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            collection_name, slot_name = row[0].split("/")
            if "rack" in slot_name.lower():
                collection_type = "rack"
            elif "table" in slot_name.lower() or "t" in collection_name:
                collection_type = "table"
            else:
                collection_type = "other"

            slot = Slot(
                tag=row[0],
                origin_pose=Pose(
                    position=Point(x=float(row[2]), y=float(row[3]), z=float(row[4])),
                    orientation=Quaternion(
                        x=float(row[5]),
                        y=float(row[6]),
                        z=float(row[7]),
                        w=float(row[8]),
                    ),
                ),
            )
            if collection_name not in slots_collections:
                slot_collection = SlotsCollection(
                    tag=collection_name, collection_type=collection_type
                )
                slot_collection.add_slot(slot)
                slots_collections[collection_name] = slot_collection
            else:
                slots_collections[collection_name].add_slot(slot)

    return slots_collections


def get_entities(name_filter: str) -> Optional[Dict[str, EntityState]]:
    node = rclpy.create_node("get_entities_states_client")

    client = node.create_client(GetEntitiesStates, "/get_entities_states")
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error("Service /get_entities_states not available")
        return

    request = GetEntitiesStates.Request()
    request.filters.filter = name_filter

    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future)

    response = future.result()
    entities: Dict[str, EntityState] = {}
    if response is not None:
        for i, name in enumerate(response.entities):
            entities[name] = response.states[i]
        return entities
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")
