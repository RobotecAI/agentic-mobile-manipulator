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
import random

import pandas as pd
from geometry_msgs.msg import Point, Pose, Quaternion
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    wait_for_ros2_services,
)
from tqdm import tqdm

from rai_app.environment import SceneManager

spawning_points = [
    (7.20, 7.44, 0.01, 0.0, 0.0, 0.0, 1.0),
    (2.48, 2.70, 0.00, 0.0, 0.0, 0.0, 1.0),
    (11.29, 3.14, 0.01, 0.0, 0.0, 0.0, 1.0),
    (17.76, 2.95, 0.01, 0.0, 0.0, 0.0, 1.0),
    (23.38, 7.06, 0.01, 0.0, 0.0, 0.0, 1.0),
    (24.48, 8.47, 0.01, 0.0, 0.0, 0.0, 1.0),
    (26.90, 11.55, 0.01, 0.0, 0.0, 0.0, 1.0),
    (24.50, 15.27, 0.01, 0.0, 0.0, 0.0, 1.0),
    (27.10, 21.35, 0.01, 0.0, 0.0, 0.0, 1.0),
    (27.05, 27.22, 0.01, 0.0, 0.0, 0.0, 1.0),
    (22.72, 25.47, 0.01, 0.0, 0.0, 0.0, 1.0),
    (17.94, 27.42, 0.01, 0.0, 0.0, 0.0, 1.0),
    (17.94, 20.61, 0.01, 0.0, 0.0, 0.0, 1.0),
    (17.71, 15.09, 0.01, 0.0, 0.0, 0.0, 1.0),
    (12.31, 26.86, 0.01, 0.0, 0.0, 0.0, 1.0),
    (8.64, 26.88, 0.01, 0.0, 0.0, 0.0, 1.0),
    (3.97, 25.58, 0.01, 0.0, 0.0, 0.0, 1.0),
]


def spawn_objects(
    scene_manager: SceneManager,
    num_objects: int,
    object_names: list[str],
    std_xy: float = 0.0,
    intensity: int = 1,
):
    pbar = tqdm(total=num_objects * intensity, desc="Spawning objects")
    for _ in range(num_objects):
        random_point = random.choice(spawning_points)
        for _ in range(intensity):
            random_object = random.choice(object_names)
            pose = Pose(
                position=Point(
                    x=random_point[0] + random.uniform(-std_xy, std_xy),
                    y=random_point[1] + random.uniform(-std_xy, std_xy),
                    z=random_point[2],
                ),
                orientation=Quaternion(
                    x=random_point[3],
                    y=random_point[4],
                    z=random_point[5],
                    w=random_point[6],
                ),
            )
            scene_manager.spawn_object(pose=pose, object_name=random_object)
            pbar.update(1)
    pbar.close()


def knock_ladder(scene_manager: SceneManager):
    object_name = "LadderSectionedSetUp_01"
    scene_manager.move_entity(object_name, dx=0.0, dy=0.0, dz=0.1, az=4.0, ay=4.0)


def knock_barrel(scene_manager: SceneManager):
    object_name = "PlasticBarrel1"
    scene_manager.move_entity(
        object_name, dx=0.0, dy=0.0, dz=0.1, az=0.0, ay=0.0, ax=-8.0
    )


@ROS2Context()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", type=str, choices=["spawn", "knock_ladder", "spill_oil", "knock_barrel"]
    )
    parser.add_argument(
        "--num_objects",
        type=int,
        default=5,
        help="Number of objects to spawn, when mode is spawn or spill_oil",
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear the scene before spawning objects"
    )
    parser.add_argument(
        "--std_xy",
        type=float,
        default=0.5,
        help="Standard deviation of the points of the objects",
    )
    parser.add_argument(
        "--spill_intensity",
        type=int,
        default=1,
        help="Intensity of the spill. Scales area covered by the spill.",
    )
    parser.add_argument(
        "--spawnables-file", type=str, default="scripts/resources/spawnables.csv"
    )

    args = parser.parse_args()
    connector = ROS2Connector()
    scene_manager = SceneManager(
        connector=connector,
        slots_file="scripts/resources/slots.csv",
        spawnables_file=args.spawnables_file,
    )
    # TODO: Reuse spawnables file from SceneManager class
    spawnables = pd.read_csv(args.spawnables_file)
    spawnables = spawnables[
        ~spawnables["object_name"].isin(["ego", "oilspill1", "oilspill2"])
    ]
    object_names = spawnables["object_name"].tolist()
    wait_for_ros2_services(connector, ["/spawn_entity", "/delete_entity"])

    if args.clear:
        scene_manager.clear_scene()

    if args.mode == "spawn":
        spawn_objects(scene_manager, args.num_objects, object_names, args.std_xy)
    elif args.mode == "knock_ladder":
        knock_ladder(scene_manager)
    elif args.mode == "knock_barrel":
        knock_barrel(scene_manager)
    elif args.mode == "spill_oil":
        spawn_objects(
            scene_manager,
            args.num_objects,
            ["oilspill1", "oilspill2"],
            args.std_xy,
            args.spill_intensity,
        )

    connector.shutdown()


if __name__ == "__main__":
    main()
