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

#!/usr/bin/env python3

import itertools
import random

from rai.communication.ros2 import ROS2Connector, ROS2Context
from rclpy.impl.logging_severity import LoggingSeverity
from tqdm import tqdm

from rai_app.control.kairos_controller import KairosController
from rai_app.environment import SceneManager


@ROS2Context()
def main(debug: bool = False):
    connector = ROS2Connector(
        executor_type="single_threaded", node_name="ground_truth_manipulation"
    )
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    print("SCENE MANAGER INITIALIZED")

    kairos_controller = KairosController(
        connector=connector, scene_manager=scene_manager
    )
    if debug:
        kairos_controller.logger.set_level(LoggingSeverity.DEBUG)

    print("KAIROS CONTROLLER INITIALIZED")

    scene_manager.clear_scene()

    entity_types = [
        "cardboardbox01_v01",
        "cardboardbox01_v02D",
        "cardboardbox01_v03",
        "cardboardbox02_v01",
        "cardboardbox02_v02D",
        "cardboardbox03_v01",
        "cardboardbox03_v02O",
        "cardboardbox04_v01",
        "cardboardbox05_v01",
        "cardboardbox06_v01",
        "cardboardbox07_v01",
        "cardboardbox08_v01",
    ]
    all_slot_names = []
    all_slot_names = [
        [f"{rack}/RackSlot{i}" for i in range(1, 10)]
        + [f"{rack}/RackSlot{i}" for i in range(13, 22)]
        for rack in ["I01", "I02"]
    ]
    all_slot_names = list(itertools.chain.from_iterable(all_slot_names))
    all_slot_names += [f"t3/Slot{i}" for i in range(1, 7)] + [
        f"t4/Slot{i}" for i in range(1, 7)
    ]
    random.shuffle(all_slot_names)

    spawn_slot_names = all_slot_names[: len(all_slot_names) // 2]
    target_slot_names = all_slot_names[len(all_slot_names) // 2 :]
    spawn_entity_types = [
        entity_types[i % len(entity_types)] for i in range(len(spawn_slot_names))
    ]

    simulation_names = scene_manager.populate_scene(
        spawn_slot_names, spawn_entity_types, None, 0.0, 0.1
    )

    import math

    for entity_name, target_slot_name in tqdm(
        zip(simulation_names, target_slot_names),
        total=min(len(simulation_names), len(target_slot_names)),
    ):
        kairos_controller.rotate_object(entity_name, math.pi / 2)
        # kairos_controller.move_object_to_slot(entity_name, target_slot_name)

    connector.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(**vars(args))
