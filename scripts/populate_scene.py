import argparse
import csv

import pandas as pd
from rai.communication.ros2 import ROS2Context

from scripts.scene_manager import SceneManager


def load_spawn_config(spawn_config_file):
    """
    Load spawn configuration from CSV file.
    Expected CSV format with headers: slot_name, entity_type
    """
    spawn_slot_names = []
    spawn_entity_types = []

    with open(spawn_config_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            spawn_slot_names.append(row["slot_name"])
            spawn_entity_types.append(row["entity_type"])

    return spawn_slot_names, spawn_entity_types


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

        spawn_slot_names, spawn_entity_types = load_spawn_config(
            "rai_app/resources/spawn_config.csv"
        )
        scene_manager.populate_scene(spawn_slot_names, spawn_entity_types)


if __name__ == "__main__":
    main()
