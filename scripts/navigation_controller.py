import time

import numpy as np
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

from scripts.tools import get_global_pose_from_origin, get_lookat_yaw

NAV_GRIPPING_POSE_DISTANCE = 0.80
NAV_STAGING_POSE_DISTANCE = 1.0
NAV_LOW_GRIPPING_POSE_DISTANCE = 1.0
NAV_LOW_STAGING_POSE_DISTANCE = 2.0
ARM_STAGING_POSE_DISTANCE = 0.2


class NavigationController:
    def __init__(self) -> None:
        self.navigator = BasicNavigator()
        self.logger = self.navigator.get_logger()
        pass

    def move_back(self, dist=0.2):
        """Move the robot backward by a specified distance using driveOnHeading"""
        self.navigator.driveOnHeading(-dist, -0.4 * np.sign(dist))

        while not self.navigator.isTaskComplete():
            time.sleep(0.1)
        result = self.navigator.getResult()

        if result == TaskResult.SUCCEEDED:
            self.logger.info("Going to pose successful")
        else:
            self.logger.info("Going to pose failed")

        time.sleep(1)

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
        self.navigator.goToPose(poseWithTimestamp)

        while not self.navigator.isTaskComplete():
            time.sleep(0.1)

        self.logger.info("Going to pose successful")

        time.sleep(1)
