import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)
from test_navigate_to_slot import get_all_slots

from rai_app.agents.tools import (
    IsPackageDamagedTool,
    NavigateToSlotSyncTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager
from rai_app.initialization.llms import (
    get_vlm_model,
)


@pytest.mark.parametrize(
    "slot", [slot for slot in get_all_slots() if slot.startswith("t")]
)
def test_is_package_damaged(
    slot: str,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    vlm = get_vlm_model("general")

    kairos_controller.mani_ctrl.move_arm_to_base_pose()

    is_package_damaged = IsPackageDamagedTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
        vlm=vlm,
        namespace_value="",
    )

    navigate_to_slot = NavigateToSlotSyncTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    for box_spawnable in [
        spawnable
        for spawnable in scene_manager.spawnable_to_uri
        if "box" in spawnable.lower()
    ]:
        scene_manager.clear_scene()

        scene_manager.spawn_on_spot(
            object_name=box_spawnable,
            slot_name=slot,
        )

        is_damaged = box_spawnable.endswith("D") or box_spawnable.endswith("T")

        navigate_to_slot._run(slot)

        try:
            result = is_package_damaged._run()

            assert result == is_damaged
        except Exception as e:
            pytest.fail(f"IsPackageDamagedTool raised an exception: {e}")
