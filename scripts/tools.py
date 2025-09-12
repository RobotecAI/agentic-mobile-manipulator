#!/usr/bin/env python3

import time
from typing import Type

import numpy as np

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


def get_global_pose_from_origin(local_pose: Pose, origin: Pose):
    """Given a local pose and an origin pose, return the global pose"""
    transform = TransformStamped()
    transform.header.frame_id = "odom"
    transform.transform.translation.x = origin.position.x
    transform.transform.translation.y = origin.position.y
    transform.transform.translation.z = origin.position.z
    transform.transform.rotation = origin.orientation
    return do_transform_pose(pose=local_pose, transform=transform)


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
