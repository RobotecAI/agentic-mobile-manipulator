import csv
import math
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import Point, Pose, Quaternion
from simulation_interfaces.msg import EntityState
from simulation_interfaces.srv import GetEntitiesStates


class Slot:
    def __init__(self, tag: str, origin_pose: Pose):
        """Slot is a place when an object can be placed or picked up from.
        It is always in the same spot.

        Args:
            tag (str): tag of a slot, example: slot1
            origin_pose (Pose): this is const pose that represents an origin point of a slot
            used to check if entity is in this slot
            nav2_pose (Nav2Pose): this is const pose that represents a place from which
            manipulation can be performed on the object in the slot.
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

        height_match = True if abs(entity_z - slot_z) <= 0.3 else False

        distance = math.sqrt((entity_x - slot_x) ** 2 + (entity_y - slot_y) ** 2)

        # Check if within 0.1 meter radius and on the same height
        return height_match and distance <= 0.3

    def assign_entity_to_slot(self, name: str):
        self._entity_name = name

    def remove_entity_from_slot(self):
        self._entity_name = None

    def is_obj_present(self) -> bool:
        """Check if the slot is currently in use"""
        if self._entity_name:
            return True
        else:
            return False

    def get_obj_name(self) -> Optional[str]:
        return self._entity_name

    def get_item_stored(self) -> Optional[str]:
        """
        Return item stored in object, based on name.
        If no object stored, return None
        """
        if self._entity_name:
            # NOTE (jmatejcz) assuming '__' is only present in name when item stored
            # in this object
            if "__" in self._entity_name:
                item_stored = self._entity_name.split("__")[1]
                return item_stored.lower()


class SlotsCollection:
    """Represents a collection of slots like a table or rack"""

    def __init__(self, tag: str, collection_type: str = ""):
        """
        Args:
            tag (str): Identifier for this collection, example:  "table1", "rack1"
            collection_type (str): Type of collection, example:  "table", "rack"
        """
        self.tag = tag
        self.collection_type = collection_type
        self.slots: Dict[str, Slot] = {}
        # item type stored in tis collection
        self.item_type: Optional[str] = None

    def add_slot(self, slot: Slot) -> None:
        """Add a slot to this collection"""
        self.slots[slot.tag] = slot

    def get_slot(self, tag: str) -> Optional[Slot]:
        """Get a specific slot by tag"""
        return self.slots.get(tag)

    def get_all_slots(self) -> Dict[str, Slot]:
        """Get all slots in this collection"""
        return self.slots.copy()

    def find_empty_slots(self) -> List[Slot]:
        """Find all empty slots in this collection"""
        empty_slots = []
        for _, slot in self.slots.items():
            if not slot.is_obj_present():
                empty_slots.append(slot)
        return empty_slots

    def find_used_slots(self) -> List[Slot]:
        """Find all used slots in this collection"""
        used_slots = []
        for _, slot in self.slots.items():
            if slot.is_obj_present():
                used_slots.append(slot)
        return used_slots

    def get_slot_with_object(self, obj_name: str) -> Optional[Slot]:
        """Find the slot containing a specific object"""
        for slot in self.slots.values():
            if slot.get_obj_name() == obj_name:
                return slot
        return None

    def find_slots_with_item_type(self, item_type: str) -> List[Slot]:
        """
        Find all slots in this collection that have
        object with ceratin item type inside
        """
        slots_with_item_type = []
        for _, slot in self.slots.items():
            if item_type.lower() == slot.get_item_stored():
                slots_with_item_type.append(slot)
        return slots_with_item_type

    def get_usage_summary(self) -> Dict[str, int]:
        """Get usage summary for this collection"""
        total_count = len(self.slots)
        used_count = sum(1 for slot in self.slots.values() if slot.is_obj_present())
        free_count = total_count - used_count

        return {
            "total": total_count,
            "used": used_count,
            "free": free_count,
        }

    @property
    def middle(self) -> Pose:
        """Calculate and return the average pose of all slots in this collection"""
        if not self.slots:
            return Pose()

        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        count = len(self.slots)

        for slot in self.slots.values():
            total_x += slot.origin_pose.position.x
            total_y += slot.origin_pose.position.y
            total_z += slot.origin_pose.position.z

        # Calculate averages
        avg_pose = Pose()
        avg_pose.position = Point(
            x=total_x / count, y=total_y / count, z=total_z / count
        )

        # For orientation, use the first slot's orientation
        first_slot = next(iter(self.slots.values()))
        avg_pose.orientation = Quaternion(
            x=first_slot.origin_pose.orientation.x,
            y=first_slot.origin_pose.orientation.y,
            z=first_slot.origin_pose.orientation.z,
            w=first_slot.origin_pose.orientation.w,
        )

        return avg_pose

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        summary = self.get_usage_summary()
        return f"{self.tag} ({self.collection_type}): {summary['used']}/{summary['total']} used"


def get_all_slots_from_file(filepath: str) -> Dict[str, SlotsCollection]:
    """Make call to simulation to retrieve all slots"""
    # NOTE (jmatejcz) simulaiton publishes once all slots and their coords to ros topic
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
