import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)

from rai_app.agents.tools import (
    NavigateToSlotSyncTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager

# Slots excluded due to racks orientation - one side is near the wall
PARTIALLY_UNAVAILABLE_RACKS = {"L": [1, 10], "G": [1, 6], "A": [1, 6], "F": [1, 10]}
RACK_TO_UNAVAILABLE_SLOTS = {
    "L": [1, 12],
    "G": [13, 24],
    "A": [13, 24],
    "F": [13, 24],
}

# Slots excluded due to warehouse layout
EXCLUDED_SLOT_NAMES = [
    "A01/RackSlot1",
    "A01/RackSlot4",
    "A01/RackSlot7",
    "G06/RackSlot3",
    "G06/RackSlot6",
    "G06/RackSlot9",
]


def get_partially_unavailable_slots():
    unavailable_slots: list[str] = []
    for rack_letter in PARTIALLY_UNAVAILABLE_RACKS:
        rack_range = list(
            range(
                PARTIALLY_UNAVAILABLE_RACKS[rack_letter][0],
                PARTIALLY_UNAVAILABLE_RACKS[rack_letter][1] + 1,
            )
        )
        rack_range = list(map(lambda x: str(x).zfill(2), rack_range))
        rack_names = [f"{rack_letter}{x}" for x in rack_range]
        for rack_name in rack_names:
            rack_slots = [
                f"{rack_name}/RackSlot{x}"
                for x in range(
                    RACK_TO_UNAVAILABLE_SLOTS[rack_letter][0],
                    RACK_TO_UNAVAILABLE_SLOTS[rack_letter][1] + 1,
                )
            ]
            unavailable_slots.extend(rack_slots)
    return sorted(unavailable_slots + EXCLUDED_SLOT_NAMES)


def get_all_slots():
    connector = ROS2Connector(executor_type="single_threaded")
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )

    slots = scene_manager.get_all_slots()
    slots_tags = [slot.tag for slot in slots.values()]

    # the following list must be equal to the one used in WarehouseTool.filter_for_slots_in_arm_range
    excluded_slot_names = {
        "RackSlot10",
        "RackSlot11",
        "RackSlot12",
        "RackSlot22",
        "RackSlot23",
        "RackSlot24",
    }
    # if any slot name contains any of the excluded slot names, it is excluded
    filtered_slots_tags: list[str] = [
        slot_tag
        for slot_tag in slots_tags
        if not any(
            excluded_slot_name in slot_tag for excluded_slot_name in excluded_slot_names
        )
    ]
    unavailable_slots = get_partially_unavailable_slots()
    filtered_slots_tags = [
        slot_tag
        for slot_tag in filtered_slots_tags
        if slot_tag not in unavailable_slots
    ]
    return sorted(filtered_slots_tags)


@pytest.mark.navigate_to_slot
@pytest.mark.parametrize("slot_name", get_all_slots())
def test_navigate_to_slot(
    slot_name: str,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    entities = scene_manager.get_entities(name_filter="box")
    if entities:
        scene_manager.assign_entities_to_slots(entities)

    navigate_to_slot = NavigateToSlotSyncTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    result = navigate_to_slot._run(slot_name)
    assert "Successfully" in result, f"NavigateToSlotSyncTool failed: {result}"
