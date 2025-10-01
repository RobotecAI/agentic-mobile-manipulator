import time
from typing import Any, Callable

import numpy as np
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from rai.communication.ros2 import ROS2Connector, ROS2Message

from scripts.tools import get_global_pose_from_origin, get_lookat_yaw


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

        if self.result is None:
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

        if self.result is None:
            raise RuntimeError("Result should not be None")

        return self.result

    def get_logger(self):
        return self.connector.node.get_logger()


class NavigationController:
    def __init__(self, connector: ROS2Connector) -> None:
        self.navigator = Navigator(connector)
        self.connector = connector
        self.costmap_cache = None
        self.costmap_metadata = None

    def _fetch_costmap(self):
        """Fetch and cache costmap as numpy array"""
        msg = ROS2Message(payload={})

        response = self.connector.call_service(
            msg,
            target="/global_costmap/get_costmap",
            timeout_sec=3,
            msg_type="nav2_msgs/srv/GetCostmap",
        ).payload
        if response:
            metadata = response.map.metadata
            costmap = np.array(response.map.data, dtype=np.uint8).reshape(
                (metadata.size_y, metadata.size_x)
            )
            self.costmap_cache = costmap
            self.costmap_metadata = metadata
            return costmap, metadata

        return None, None

    def is_position_available(self, position: Point, threshold: int = 253) -> bool:
        """
        Check if world position is available in costmap.
        Everything below threshold is considered available.
        """
        if self.costmap_cache is None:
            self._fetch_costmap()
        logger = self.navigator.get_logger()
        if self.costmap_cache is None or self.costmap_metadata is None:
            logger.warning(
                "Could not access costmap and check if position available. Assuming it is... "
            )
            return True

        meta = self.costmap_metadata
        grid_x = int((position.x - meta.origin.position.x) / meta.resolution)
        grid_y = int((position.y - meta.origin.position.y) / meta.resolution)

        if 0 <= grid_x < meta.size_x and 0 <= grid_y < meta.size_y:
            return self.costmap_cache[grid_y, grid_x] < threshold
        return False

    def move_back(self, dist=0.2):
        """Move the robot backward by a specified distance using driveOnHeading"""
        return self.navigator.drive_on_heading(
            -dist, -0.4 * np.sign(dist), time_allowance=10
        ).result

    def approach_target_keeping_distance(self, target_pose: Pose, relative_pose: Pose):
        nav_staging_pose = get_global_pose_from_origin(relative_pose, target_pose)

        return self.navigate_to_pose(
            nav_staging_pose.position,
            yaw=get_lookat_yaw(nav_staging_pose.position, target_pose.position),
        )

    def approach_target_along_orientation(
        self, target_pose: Pose, target_pose_distance: float = 0.0
    ) -> bool:
        """Approach an object pose keeping distance along its orientation"""
        result = self.approach_target_keeping_distance(
            target_pose, Pose(position=Point(x=target_pose_distance))
        )
        if result:
            return True
        else:
            return False

    def approach_target(
        self, target_pose: Pose, target_pose_distance: float = 0.0
    ) -> bool:
        """
        Approach an object pose keeping distance.
        Try aproaching from up to 4 directions if previous not available
        """
        if self.approach_target_keeping_distance(
            target_pose, Pose(position=Point(x=target_pose_distance))
        ):
            return True

        if self.approach_target_keeping_distance(
            target_pose, Pose(position=Point(x=-target_pose_distance))
        ):
            return True
        if self.approach_target_keeping_distance(
            target_pose, Pose(position=Point(y=target_pose_distance))
        ):
            return True
        if self.approach_target_keeping_distance(
            target_pose, Pose(position=Point(y=-target_pose_distance))
        ):
            return True

        return False

    def navigate_to_pose(
        self,
        position: Point,
        yaw: float = 0.0,
        frame: str = "map",
    ):
        """Navigate to certain pose

        Returns:
            bool: True if succeeded, False if not
        """
        logger = self.navigator.get_logger()
        if not self.is_position_available(position=position):
            logger.info(f"Position {position} not available")
            return
        poseWithTimestamp = PoseStamped()
        poseWithTimestamp.pose = Pose(
            position=position,
            orientation=Quaternion(x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)),
        )
        poseWithTimestamp.header.frame_id = frame
        poseWithTimestamp.header.stamp = (
            self.navigator.connector.node.get_clock().now().to_msg()
        )
        return self.navigator.navigate_to_pose(poseWithTimestamp)
