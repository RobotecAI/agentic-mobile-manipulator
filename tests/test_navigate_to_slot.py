import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)

from rai_app.agents.tools import (
    NavigateToSlotSyncTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager


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
