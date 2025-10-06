import argparse
import csv
import random

import pandas as pd
from geometry_msgs.msg import Point, Pose
from rai.communication.ros2 import ROS2Context

from scripts.scene_manager import SceneManager


def generate_spawn_config_for_racks(
    collections_assignments_file: str,
    output_file: str,
    num_rack_slots_per_rack: int = 24,
    fill_percentage: float = 0.7,
    mismatch_percentage: float = 0.2,
):
    """
    Generate spawn configuration from rack assignments.

    Args:
        rack_assignments_file: CSV file with collection_name,item_type columns
        output_file: Output CSV file path
        num_table_slots: Number of slots per table
        num_rack_slots_per_rack: Number of slots per rack
        fill_percentage: Percentage of slots to fill (0.0 to 1.0)
        mismatch_percentage: Percentage of items that don't match rack type (0.0 to 1.0)
    """

    entity_types = ["cardboardbox01_v01", "cardboardbox01_v02D", "cardboardbox05_v01"]
    all_item_types = ["cpu", "gpu", "motherboard", "pipes", "nails", "hammers"]

    rack_to_item = {}
    with open(collections_assignments_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rack_to_item[row["collection_name"]] = row["item_type"]

    spawn_data = []

    for coll_name, rack_item_type in rack_to_item.items():
        # Determine how many slots to fill for this rack
        num_slots_to_fill = int(num_rack_slots_per_rack * fill_percentage)

        # Randomly select which slot numbers to use
        slot_numbers = random.sample(
            range(1, num_rack_slots_per_rack + 1), num_slots_to_fill
        )

        for slot_num in slot_numbers:
            slot_name = f"{coll_name}/RackSlot{slot_num}"
            entity_type = random.choice(entity_types)

            # Decide if this should be a matching or mismatching item
            if random.random() < mismatch_percentage:
                # Mismatch: choose a different item type
                other_items = [
                    item for item in all_item_types if item != rack_item_type
                ]
                item = random.choice(other_items)
            else:
                # Match: use the rack's designated item type
                item = rack_item_type

            spawn_data.append(
                {"slot_name": slot_name, "entity_type": entity_type, "item": item}
            )

    with open(output_file, "w", newline="") as file:
        fieldnames = ["slot_name", "entity_type", "item"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(spawn_data)


def load_spawn_config(spawn_config_file):
    """
    Load spawn configuration from CSV file.
    Expected CSV format with headers: slot_name, entity_type
    """
    spawn_slot_names = []
    spawn_entity_types = []
    items_stored = []

    with open(spawn_config_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            spawn_slot_names.append(row["slot_name"])
            spawn_entity_types.append(row["entity_type"])
            items_stored.append(row["item"])

    return spawn_slot_names, spawn_entity_types, items_stored


def load_item_type_assignment_file(assignment_file: str):
    collection_names = []
    item_types = []
    with open(assignment_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            collection_names.append(row["collection_name"])
            item_types.append(row["item_type"])
    return collection_names, item_types


def load_entity_types(entity_types_file):
    """
    Load entity types from CSV file and generate spawn pattern.
    Expected CSV format with header: entity_type
    """
    entity_types = []

    with open(entity_types_file, "r") as file:
        reader = csv.DictReader(file)
        entity_types = [row["entity_type"] for row in reader]

    return entity_types


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

    slots = slots[~slots["slot_name"].str.contains(r"t\d+/Slot\d+")]
    slots = slots[~slots["slot_name"].str.contains(r"RackSlot5")]

    # object_names = [
    #     random.choice(list(spawnables["object_name"].tolist()))
    #     for _ in range(len(slots))
    # ]

    # slot_names = slots["slot_name"].tolist()
    if args.clear:
        scene_manager.clear_scene()
    if args.spawn:
        # scene_manager.populate_scene(slot_names, object_names)
        # generate_spawn_config_for_racks(
        #     rack_assignments_file="rai_app/resources/rack_assignment.csv",
        #     output_file="rai_app/resources/spawn_config_racks.csv",
        # )
        spawn_slot_names, spawn_entity_types, items_stored = load_spawn_config(
            "rai_app/resources/spawn_config_racks.csv"
        )
        scene_manager.populate_scene(spawn_slot_names, spawn_entity_types, items_stored)

    ### spawn trash
    pose = Pose(
        position=Point(x=14.240, y=17.230, z=0.023),
    )
    scene_manager.spawn_object(pose=pose, object_name="cardboardbox03_v02O")

    # pose = Pose(
    #     position=Point(x=21.240, y=1.930, z=0.023),
    # )
    # scene_manager.spawn_object(pose=pose, object_name="cardboardbox03_v02O")

    pose = Pose(
        position=Point(x=19.240, y=4.230, z=0.023),
    )
    scene_manager.spawn_object(pose=pose, object_name="cardboardbox03_v02O")
    scene_manager.connector.shutdown()


if __name__ == "__main__":
    main()
