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

import argparse
import csv

from geometry_msgs.msg import Point, Pose
from rai.communication.ros2 import ROS2Connector, ROS2Context

from rai_app.control.kairos_controller import (
    NAV_GRIPPING_POSE_DISTANCE,
    KairosController,
)
from rai_app.environment import SceneManager


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
    parser.add_argument("--slots-file", type=str, default="scripts/resources/slots.csv")
    parser.add_argument(
        "--spawnables-file", type=str, default="scripts/resources/spawnables.csv"
    )
    args = parser.parse_args()

    scene_manager = SceneManager(
        slots_file=args.slots_file, spawnables_file=args.spawnables_file
    )
    scene_manager.clear_scene()

    ### spawn trash
    trash_poses = [
        Pose(
            position=Point(x=18.240, y=4.230, z=0.023),
        ),
        Pose(
            position=Point(x=13.240, y=7.230, z=0.023),
        ),
        Pose(
            position=Point(x=19.240, y=15.230, z=0.023),
        ),
    ]
    for pose in trash_poses:
        scene_manager.spawn_object(pose=pose, object_name="cardboardbox03_v02O")

    connector = ROS2Connector(
        executor_type="single_threaded", node_name="navigate_between_trash"
    )
    controller = KairosController(connector=connector)

    for trash_pose in trash_poses:
        print(f"Navigating to staging pose {trash_pose}")
        controller.nav_ctrl.navigate_to_target_pose(
            trash_pose, NAV_GRIPPING_POSE_DISTANCE
        )


if __name__ == "__main__":
    main()
