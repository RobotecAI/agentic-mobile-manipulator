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

#!/usr/bin/env python3

import copy
import math
import time
from typing import Type

import numpy as np
import tf_transformations

# generic ros libraries
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.tools import BaseTool
from moveit.core.kinematic_constraints import construct_joint_constraint
from moveit.core.robot_state import RobotState

# moveit python library
from moveit.planning import (
    MoveItPy,
    PlanningComponent,
)
from nav2_simple_commander.robot_navigator import BasicNavigator
from pydantic import BaseModel, Field
from tf2_geometry_msgs import TransformStamped, do_transform_pose
from tf_transformations import euler_from_quaternion


def get_global_pose_from_origin(local_pose: Pose, origin: Pose):
    """Compute a global pose from a local pose and origin transform.

    Parameters
    ----------
    local_pose : Pose
        Pose expressed in the local frame that should be transformed.
    origin : Pose
        Reference pose that defines the transform to the global frame.

    Returns
    -------
    Pose
        Pose expressed in the global coordinate frame.
    """
    transform = TransformStamped()
    transform.header.frame_id = "odom"
    transform.transform.translation.x = origin.position.x
    transform.transform.translation.y = origin.position.y
    transform.transform.translation.z = origin.position.z
    transform.transform.rotation = origin.orientation
    return do_transform_pose(pose=local_pose, transform=transform)


def calculate_relative_transform(from_pose: Pose, to_pose: Pose) -> Pose:
    """Compute the relative transform between two poses.

    Parameters
    ----------
    from_pose : Pose
        Source pose expressed in the reference frame.
    to_pose : Pose
        Target pose expressed in the same frame as ``from_pose``.

    Returns
    -------
    Pose
        Relative transform that maps ``from_pose`` to ``to_pose``.
    """

    # Convert quaternions to transformation matrices
    from_quat = [
        from_pose.orientation.x,
        from_pose.orientation.y,
        from_pose.orientation.z,
        from_pose.orientation.w,
    ]
    to_quat = [
        to_pose.orientation.x,
        to_pose.orientation.y,
        to_pose.orientation.z,
        to_pose.orientation.w,
    ]

    from_matrix = tf_transformations.quaternion_matrix(from_quat)
    to_matrix = tf_transformations.quaternion_matrix(to_quat)

    # Set translation components
    from_matrix[0, 3] = from_pose.position.x
    from_matrix[1, 3] = from_pose.position.y
    from_matrix[2, 3] = from_pose.position.z

    to_matrix[0, 3] = to_pose.position.x
    to_matrix[1, 3] = to_pose.position.y
    to_matrix[2, 3] = to_pose.position.z

    # Calculate relative transform: T_relative = T_from^-1 * T_to
    relative_matrix = np.linalg.inv(from_matrix) @ to_matrix

    # Extract translation and rotation from the relative transform
    relative_translation = relative_matrix[:3, 3]
    relative_quat = tf_transformations.quaternion_from_matrix(relative_matrix)

    # Create and return the relative pose
    relative_pose = Pose()
    relative_pose.position.x = relative_translation[0]
    relative_pose.position.y = relative_translation[1]
    relative_pose.position.z = relative_translation[2]
    relative_pose.orientation.x = relative_quat[0]
    relative_pose.orientation.y = relative_quat[1]
    relative_pose.orientation.z = relative_quat[2]
    relative_pose.orientation.w = relative_quat[3]

    return relative_pose


def rotate_pose(pose: Pose, angle, direction, point=None):
    """Rotate a pose around an arbitrary axis and reference point.

    Parameters
    ----------
    pose : Pose
        Pose to be rotated.
    angle : float
        Rotation angle in radians.
    direction : Sequence[float]
        Three-element iterable describing the rotation axis.
    point : Sequence[float], optional
        Three-element iterable describing the rotation origin. Defaults to
        the pose position when ``None``.

    Returns
    -------
    Pose
        Rotated pose in the original frame.
    """
    # If no point specified, rotate around the pose's own position
    if point is None:
        point = [pose.position.x, pose.position.y, pose.position.z]
    # Convert pose position and orientation to transformation matrix
    quat = [
        pose.orientation.x,
        pose.orientation.y,
        pose.orientation.z,
        pose.orientation.w,
    ]
    pose_matrix = tf_transformations.quaternion_matrix(quat)
    pose_matrix[0, 3] = pose.position.x
    pose_matrix[1, 3] = pose.position.y
    pose_matrix[2, 3] = pose.position.z

    # Get rotation matrix
    rot_matrix = tf_transformations.rotation_matrix(angle, direction, point)

    # Apply rotation: T_rotated = T_rotation * T_pose
    rotated_matrix = rot_matrix @ pose_matrix

    # Extract new position and orientation
    new_pose = copy.deepcopy(pose)
    new_pose.position.x = rotated_matrix[0, 3]
    new_pose.position.y = rotated_matrix[1, 3]
    new_pose.position.z = rotated_matrix[2, 3]
    new_quat = tf_transformations.quaternion_from_matrix(rotated_matrix)
    new_pose.orientation.x = new_quat[0]
    new_pose.orientation.y = new_quat[1]
    new_pose.orientation.z = new_quat[2]
    new_pose.orientation.w = new_quat[3]
    return new_pose


def get_yaw_difference(pose1: Pose, pose2: Pose):
    q1 = pose1.orientation
    q2 = pose2.orientation
    roll1, pitch1, yaw1 = euler_from_quaternion([q1.x, q1.y, q1.z, q1.w])
    roll2, pitch2, yaw2 = euler_from_quaternion([q2.x, q2.y, q2.z, q2.w])
    yaw_diff = yaw2 - yaw1
    # normalize to [-pi, pi]
    yaw_diff = math.atan2(math.sin(yaw_diff), math.cos(yaw_diff))
    return yaw_diff


def apply_relative_transform(base_pose: Pose, relative_transform: Pose) -> Pose:
    """Apply a relative transform to a base pose.

    Parameters
    ----------
    base_pose : Pose
        Pose expressed in a reference frame.
    relative_transform : Pose
        Relative transform to apply to ``base_pose``.

    Returns
    -------
    Pose
        Resulting pose after applying the relative transform.
    """
    # Convert poses to transformation matrices
    base_quat = [
        base_pose.orientation.x,
        base_pose.orientation.y,
        base_pose.orientation.z,
        base_pose.orientation.w,
    ]
    rel_quat = [
        relative_transform.orientation.x,
        relative_transform.orientation.y,
        relative_transform.orientation.z,
        relative_transform.orientation.w,
    ]

    base_matrix = tf_transformations.quaternion_matrix(base_quat)
    rel_matrix = tf_transformations.quaternion_matrix(rel_quat)

    # Set translation components
    base_matrix[0, 3] = base_pose.position.x
    base_matrix[1, 3] = base_pose.position.y
    base_matrix[2, 3] = base_pose.position.z

    rel_matrix[0, 3] = relative_transform.position.x
    rel_matrix[1, 3] = relative_transform.position.y
    rel_matrix[2, 3] = relative_transform.position.z

    # Apply transform: T_result = T_base * T_relative
    result_matrix = base_matrix @ rel_matrix

    # Extract translation and rotation
    result_translation = result_matrix[:3, 3]
    result_quat = tf_transformations.quaternion_from_matrix(result_matrix)

    # Create and return the result pose
    result_pose = Pose()
    result_pose.position.x = result_translation[0]
    result_pose.position.y = result_translation[1]
    result_pose.position.z = result_translation[2]
    result_pose.orientation.x = result_quat[0]
    result_pose.orientation.y = result_quat[1]
    result_pose.orientation.z = result_quat[2]
    result_pose.orientation.w = result_quat[3]

    return result_pose


class MoveToPointToolInput(BaseModel):
    x: float = Field(description="The x coordinate of the point to move to")
    y: float = Field(description="The y coordinate of the point to move to")
    z: float = Field(description="The z coordinate of the point to move to")


class MoveToPointTool(BaseTool):
    name: str = "move_to_point"
    description: str = (
        "Guide the robot's end effector to a specific point within the manipulator's operational space. "
        "This tool ensures precise movement to the desired location. "
        "While it confirms successful positioning, please note that it doesn't provide feedback on the "
        "success of grabbing or releasing objects. Use additional sensors or tools for that information."
    )

    manipulator_frame: str = Field(..., description="Manipulator frame")
    moveitpy: MoveItPy
    planning_component: PlanningComponent
    pose_link: str
    additional_height: float = Field(
        default=0.05, description="Additional height for the place task [m]"
    )

    # constant quaternion
    quaternion: Quaternion = Field(
        default=Quaternion(x=0.9238795325112867, y=-0.3826834323650898, z=0.0, w=0.0),
        description="Constant quaternion",
    )

    args_schema: Type[MoveToPointToolInput] = MoveToPointToolInput

    def _run(
        self,
        x: float,
        y: float,
        z: float,
    ) -> str:
        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = self.manipulator_frame
        pose_stamped.pose = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=self.quaternion,
        )

        self.planning_component.set_start_state_to_current_state()
        self.planning_component.set_goal_state(
            pose_stamped_msg=pose_stamped, pose_link=self.pose_link
        )

        plan = self.planning_component.plan()

        if plan:
            self.moveitpy.execute(plan.trajectory, controllers=[])
        else:
            return "Failed to plan the trajectory."

        return f"End effector successfully positioned at coordinates ({x:.2f}, {y:.2f}, {z:.2f})."

    def set_joint_values(self, joint_values):
        robot_model = self.moveitpy.get_robot_model()
        robot_state = RobotState(robot_model)
        robot_state.joint_positions = joint_values
        joint_constraint = construct_joint_constraint(
            robot_state=robot_state,
            joint_model_group=robot_model.get_joint_model_group(
                self.planning_component.planning_group_name
            ),
        )

        self.planning_component.set_start_state_to_current_state()
        self.planning_component.set_goal_state(
            motion_plan_constraints=[joint_constraint]
        )

        plan = self.planning_component.plan()

        if plan:
            self.moveitpy.execute(plan.trajectory, controllers=[])
        else:
            return "Failed to plan the trajectory."

        return f"End effector successfully positioned at joint values ({joint_values})."


def navigate_to_pose(
    position: Point,
    yaw: float = 0.0,
    frame: str = "map",
):
    navigator = BasicNavigator()
    poseWithTimestamp = PoseStamped()
    poseWithTimestamp.pose = Pose(
        position=position,
        orientation=Quaternion(x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)),
    )
    poseWithTimestamp.header.frame_id = frame
    navigator.goToPose(poseWithTimestamp)
    while not navigator.isTaskComplete():
        time.sleep(0.1)
    print("Going to pose successful")

    time.sleep(1)


def get_lookat_yaw(origin: Point, target: Point) -> float:
    direction = np.array(
        [
            target.x - origin.x,
            target.y - origin.y,
        ]
    )
    yaw = np.arctan2(direction[1], direction[0])
    return yaw
