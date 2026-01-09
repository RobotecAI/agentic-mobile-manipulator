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

import itertools
import random

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


@pytest.mark.parametrize("from_coll,to_coll", get_rack_pairs())
def test_coll_to_coll(
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


LEVELS = ["low", "mid", "midhigh", "high"]
LEVEL_SLOTS = {
    "low": [f"RackSlot{i}" for i in [1, 2, 3, 13, 14, 15]],
    "mid": [f"RackSlot{i}" for i in [4, 5, 6, 16, 17, 18]],
    "midhigh": [f"Slot{i}" for i in range(1, 13)],
    "high": [f"RackSlot{i}" for i in [7, 8, 9, 19, 20, 21]],
}


def get_all_coll_slots_except_on_level(
    coll: str, level: str, scene_manager: SceneManager
):
    return [
        slot
        for slot in scene_manager.get_all_slots()
        if slot.startswith(coll) and not slot.endswith(tuple(LEVEL_SLOTS[level]))
    ]


@pytest.mark.parametrize("from_,to_", list(itertools.product(LEVELS, LEVELS)))
def test_level_movement(
    from_: str,
    to_: str,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    """Spawn a single box to test level-to-level movement."""

    if from_ == "midhigh":
        spawn_coll = "t3"
    else:
        spawn_coll = "J01"

    if to_ == "midhigh":
        target_coll = "t3"
    else:
        target_coll = "J02"

    scene_manager.clear_scene()

    spawnables = [
        spawnable
        for spawnable in scene_manager.spawnable_to_uri
        if "box" in spawnable.lower() and not spawnable.endswith("T")
    ]

    spawnable = random.choice(spawnables)
    spawn_slots = [
        slot
        for slot in scene_manager.get_all_slots()
        if slot.startswith(spawn_coll) and slot.endswith(tuple(LEVEL_SLOTS[from_]))
    ]
    scene_manager.spawn_on_spot(
        object_name=spawnable,
        slot_name=random.choice(spawn_slots),
    )

    target_slots = get_all_coll_slots_except_on_level(
        coll=target_coll,
        level=to_,
        scene_manager=scene_manager,
    )
    for slot in target_slots:
        scene_manager.spawn_on_spot(
            object_name=random.choice(spawnables),
            slot_name=slot,
        )

    test_coll_to_coll(
        from_coll=spawn_coll,
        to_coll=target_coll,
        connector=connector,
        scene_manager=scene_manager,
        kairos_controller=kairos_controller,
    )
