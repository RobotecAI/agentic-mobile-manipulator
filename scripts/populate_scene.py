import argparse
import csv
import random

import pandas as pd
from geometry_msgs.msg import Point, Pose
from rai.communication.ros2 import ROS2Context
from tqdm import tqdm

from scripts.scene_manager import SceneManager


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
    parser.add_argument("--rack_fill", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--spawn-anomalies", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)

    scene_manager = SceneManager(
        slots_file=args.slots_file, spawnables_file=args.spawnables_file
    )

    slots = pd.read_csv(args.slots_file, delimiter=",")
    spawnables = pd.read_csv(args.spawnables_file, delimiter=",")
    spawnables = spawnables[~spawnables["object_name"].isin(args.filter.split("|"))]

    slots = slots[~slots["slot_name"].str.contains(r"t\d+/Slot\d+")]
    slots = slots[~slots["slot_name"].str.contains(r"RackSlot5")]

    if args.clear:
        scene_manager.clear_scene()
    if args.spawn:
        rack_config = pd.read_csv(
            "rai_app/resources/rack_assignment.csv", delimiter=","
        )
        item_type_assets = pd.read_csv(
            "rai_app/resources/item_type_assets.csv", delimiter=","
        )
        item_type_assets["asset_names"] = item_type_assets["asset_names"].str.split(";")

        spawn_slot_names = []
        spawn_entity_types = []
        items_stored = []
        for rack, item_type in zip(
            rack_config["collection_name"].tolist(), rack_config["item_type"].tolist()
        ):
            slots_of_rack = scene_manager.get_collection(rack).get_all_slots().values()
            for slot in slots_of_rack:
                if random.random() > args.rack_fill:
                    continue
                spawn_slot_names.append(slot.tag)
                spawn_entity_types.append(
                    random.choice(
                        item_type_assets.loc[
                            item_type_assets["item_type"] == item_type, "asset_names"
                        ].values[0]
                    )
                )
                items_stored.append(item_type)

        scene_manager.populate_scene(
            spawn_slot_names, spawn_entity_types, items_stored, std_yaw=0.0
        )
        spawn_slot_names, spawn_entity_types, items_stored = load_spawn_config(
            "rai_app/resources/spawn_config_table.csv"
        )

        scene_manager.populate_scene(
            spawn_slot_names, spawn_entity_types, items_stored, std_yaw=0.0
        )

    anomalies_poses = [
        Pose(
            position=Point(x=10.240, y=5.0, z=0.023),
        ),
        Pose(
            position=Point(x=15.240, y=9.0, z=0.023),
        ),
        Pose(
            position=Point(x=18.240, y=3.0, z=0.023),
        ),
    ]
    anomalies_types = [
        "cardboardbox02_v01T",
        "cardboardbox03_v01",
        "cardboardbox01_v01",
    ]

    if args.spawn_anomalies:
        for pose, anomaly_type in tqdm(
            zip(anomalies_poses, anomalies_types), desc="Spawning anomalies"
        ):
            scene_manager.spawn_object(pose=pose, object_name=anomaly_type)
    scene_manager.connector.shutdown()


if __name__ == "__main__":
    main()
