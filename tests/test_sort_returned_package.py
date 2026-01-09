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

import random

import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)

from rai_app.agents.tools import (
    SortReturnedPackageTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager
from rai_app.initialization.llms import (
    get_vlm_model,
)


def test_sort_returned_package(
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    vlm = get_vlm_model("general")

    sort_tool = SortReturnedPackageTool(
        vlm=vlm,
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    spawnables = [
        spawnable
        for spawnable in scene_manager.spawnable_to_uri
        if "box" in spawnable.lower()
    ]

    scene_manager.clear_scene()

    slots = [slot for slot in scene_manager.get_all_slots() if slot.startswith("t1")]
    random.shuffle(slots)

    num_packages = 5
    for spawnable, slot in random.choices(list(zip(spawnables, slots)), k=num_packages):
        scene_manager.spawn_on_spot(slot, spawnable)

    try:
        for _ in range(num_packages):
            result = sort_tool._run()

            assert "Moved" in result, f"SortReturnedPackageTool failed: {result}"

    except Exception as e:
        pytest.fail(f"SortReturnedPackageTool failed: {e}")
