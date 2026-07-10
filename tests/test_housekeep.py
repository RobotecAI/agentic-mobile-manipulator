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
    HouseKeepTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager


def get_racks():
    connector = ROS2Connector(executor_type="single_threaded")
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    racks = sorted(
        list(
            set(
                slot.split("/")[0]
                for slot in scene_manager.get_all_slots()
                if "Garbage" not in slot
            )
        )
    )
    return racks


@pytest.mark.parametrize("rack", get_racks())
def test_single_box_housekeeping(
    rack: str,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    housekeep_tool = HouseKeepTool(
        task_topic="housekeep_test",
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    spawnables = [
        spawnable
        for spawnable in scene_manager.spawnable_to_uri
        if "box" in spawnable.lower() and not spawnable.endswith(("T", "D"))
    ]

    spawnable = random.choice(spawnables)

    scene_manager.clear_scene()

    slots = [slot for slot in scene_manager.get_all_slots() if slot.startswith(rack)]
    slot = random.choice(slots)

    scene_manager.spawn_on_spot(slot, spawnable, std_yaw=100.0)

    try:
        result = housekeep_tool._run(rack)
        assert "successfully" in result, f"HouseKeepTool failed: {result}"
    except Exception as e:
        scene_manager.reset_simulation()
        pytest.fail(f"HouseKeepTool failed: {e}")
