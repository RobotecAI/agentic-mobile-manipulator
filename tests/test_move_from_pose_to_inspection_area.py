import random

import pytest
from geometry_msgs.msg import Point, Pose
from rai.communication.ros2 import (
    ROS2Connector,
)

from rai_app.agents.tools import (
    MoveFromPoseToInspectionAreaTool,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager

SPAWN_POSES = [
    Pose(position=Point(x=17.53, y=14.19)),
    Pose(position=Point(x=22.5, y=15.0)),
    Pose(position=Point(x=17.4, y=4.0)),
    Pose(position=Point(x=7.3, y=7.2)),
    Pose(position=Point(x=10.9, y=2.2)),
    Pose(position=Point(x=22.6, y=27.7)),
    Pose(position=Point(x=27.7, y=27.6)),
]


@pytest.mark.parametrize("spawn_pose_id", range(len(SPAWN_POSES)))
def test_move_from_pose_to_inspection_area(
    spawn_pose_id: int,
    connector: ROS2Connector,
    scene_manager: SceneManager,
    kairos_controller: KairosController,
):
    spawn_pose = SPAWN_POSES[spawn_pose_id]

    move_from_pose_to_inspection_area = MoveFromPoseToInspectionAreaTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    spawnables = [
        spawnable
        for spawnable in scene_manager.spawnable_to_uri
        if "box" in spawnable.lower()
    ]

    spawnable = random.choice(spawnables)

    scene_manager.clear_scene()

    object_name = scene_manager.spawn_object(pose=spawn_pose, object_name=spawnable)

    gripping_point = scene_manager.get_top_gripping_point(object_name).position

    try:
        result = move_from_pose_to_inspection_area._run(
            x=gripping_point.x, y=gripping_point.y, z=gripping_point.z
        )

        assert "Successfully" in result, (
            f"MoveFromPoseToInspectionAreaTool failed: {result}"
        )
    except Exception as e:
        pytest.fail(f"MoveFromPoseToInspectionAreaTool failed: {e}")
