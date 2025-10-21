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

import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)

from rai_app.agents.tools import (
    MoveFromCollectionToCollectionTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager


def get_rack_pairs():
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
    return list(zip(racks[:-1], racks[1:]))


@pytest.mark.coll_to_coll
@pytest.mark.parametrize("from_coll,to_coll", get_rack_pairs())
def test_move_tool(
    from_coll: str,
    to_coll: str,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    entities = scene_manager.get_entities(name_filter="box")
    if entities:
        scene_manager.assign_entities_to_slots(entities)

    move_from_coll_to_coll = MoveFromCollectionToCollectionTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    result = move_from_coll_to_coll._run(from_coll, to_coll)
    assert "Successfully" in result, (
        f"MoveFromCollectionToCollectionTool failed: {result}"
    )
