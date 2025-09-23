import time
from typing import Any, Callable

import numpy as np
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from rai.communication.ros2 import ROS2Connector, ROS2Message

from scripts.tools import get_global_pose_from_origin, get_lookat_yaw

NAV_GRIPPING_POSE_DISTANCE = 0.80
NAV_STAGING_POSE_DISTANCE = 1.0
NAV_LOW_GRIPPING_POSE_DISTANCE = 1.0
NAV_LOW_STAGING_POSE_DISTANCE = 2.0
ARM_STAGING_POSE_DISTANCE = 0.2


class Navigator:
    def __init__(self, connector: ROS2Connector):
        self.connector = connector
        self.done: bool = False
        self.feedback: Any = None
        self.result: Any = None

    def run_start_action(
        self,
        action_data: ROS2Message,
        target: str,
        msg_type: str,
        on_feedback: Callable[[Any], None],
        on_done: Callable[[Any], None],
    ):
        for _ in range(3):
            try:
                return self.connector.start_action(
                    action_type=msg_type,
                    action_data=action_data,
                    msg_type=msg_type,
                    target=target,
                    on_feedback=on_feedback,
                    on_done=on_done,
                )
            except RuntimeError:
                self.connector.logger.error("Failed to start nav2 action, retrying...")
                time.sleep(1)
                continue
        raise RuntimeError("Failed to start action")

    def reset_state(self):
        self.done = False
        self.feedback = None
        self.result = None

    def feedback_callback(self, feedback):
        self.feedback = feedback

    def done_callback(self, result):
        self.done = True
        self.result = result

    def drive_on_heading(self, distance: float, speed: float, time_allowance: int = 10):
        self.reset_state()

        self.run_start_action(
            action_data=ROS2Message(
                payload={
                    "distance": distance,
                    "speed": speed,
                    "time_allowance": {"sec": time_allowance},
                }
            ),
            target="rai/nav2/drive_on_heading",
            msg_type="rai_interfaces/action/DriveOnHeading",
            on_feedback=self.feedback_callback,
            on_done=self.done_callback,
        )

        while not self.done:
            time.sleep(0.1)

        if isinstance(self.result, None):
            raise RuntimeError("Result should not be None")
        return self.result

    def navigate_to_pose(self, pose: PoseStamped):
        self.reset_state()

        self.run_start_action(
            action_data=ROS2Message(payload={"pose": pose}),
            target="rai/nav2/navigate_to_pose",
            msg_type="rai_interfaces/action/NavigateToPose",
            on_feedback=self.feedback_callback,
            on_done=self.done_callback,
        )

        while not self.done:
            time.sleep(0.1)

        if isinstance(self.result, None):
            raise RuntimeError("Result should not be None")
        return self.result

    def get_logger(self):
        return self.connector.node.get_logger()


class NavigationController:
    def __init__(self, connector: ROS2Connector) -> None:
        self.navigator = Navigator(connector)
        self.logger = self.navigator.get_logger()
        pass

    def move_back(self, dist=0.2):
        """Move the robot backward by a specified distance using driveOnHeading"""
        return self.navigator.drive_on_heading(
            -dist, -0.4 * np.sign(dist), time_allowance=10
        ).result

    def navigate_to_staging_pose(self, target_pose: Pose):
        # self.logger.debug("Navigating to staging pose")
        nav_staging_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_STAGING_POSE_DISTANCE)), target_pose
        )
        self.navigate_to_pose(
            nav_staging_pose.position,
            yaw=get_lookat_yaw(nav_staging_pose.position, target_pose.position),
        )

    def navigate_to_gripping_pose(self, target_pose: Pose):
        # self.logger.debug("Navigating to gripping pose")
        nav_gripping_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_GRIPPING_POSE_DISTANCE)), target_pose
        )
        self.navigate_to_pose(
            nav_gripping_pose.position,
            yaw=get_lookat_yaw(nav_gripping_pose.position, target_pose.position),
        )

    def navigate_to_low_staging_pose(self, target_pose: Pose):
        # self.logger.debug("Navigating to low staging pose")
        nav_staging_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_LOW_STAGING_POSE_DISTANCE)), target_pose
        )
        self.navigate_to_pose(
            nav_staging_pose.position,
            yaw=get_lookat_yaw(nav_staging_pose.position, target_pose.position),
        )

    def navigate_to_low_gripping_pose(self, target_pose: Pose):
        # self.logger.debug("Navigating to low gripping pose")
        nav_gripping_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_LOW_GRIPPING_POSE_DISTANCE)), target_pose
        )
        self.navigate_to_pose(
            nav_gripping_pose.position,
            yaw=get_lookat_yaw(nav_gripping_pose.position, target_pose.position),
        )

    def navigate_to_pose(
        self,
        position: Point,
        yaw: float = 0.0,
        frame: str = "map",
    ):
        poseWithTimestamp = PoseStamped()
        poseWithTimestamp.pose = Pose(
            position=position,
            orientation=Quaternion(x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)),
        )
        poseWithTimestamp.header.frame_id = frame
        poseWithTimestamp.header.stamp = (
            self.navigator.connector.node.get_clock().now().to_msg()
        )

        return self.navigator.navigate_to_pose(poseWithTimestamp).result
