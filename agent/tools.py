import time
from typing import cast

import numpy as np
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from nav2_simple_commander.robot_navigator import BasicNavigator
from place import Place


def navigate_to_pose(
    x: float,
    y: float,
    z: float = 0.0,
    yaw: float = 0.0,
):
    navigator = BasicNavigator()
    poseWithTimestamp = PoseStamped()
    poseWithTimestamp.pose = Pose(
        position=Point(x=x, y=y, z=z),
        orientation=Quaternion(x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)),
    )
    poseWithTimestamp.header.frame_id = "map"
    navigator.goToPose(poseWithTimestamp)
    while not navigator.isTaskComplete():
        time.sleep(0.1)
    print("Going to pose successful")


@tool
def navigate_to_place(place_name: str, config: RunnableConfig) -> str:
    """
    Navigate to the place.
    """
    place = config["configurable"]["places"].get_place_by_name(place_name)
    if place is not None:
        place = cast(Place, place)
        navigate_to_pose(place.pose.x, place.pose.y, place.pose.z, place.pose.yaw)
        return f"Navigated to place {place_name}"
    else:
        return f"Place {place_name} not found"
