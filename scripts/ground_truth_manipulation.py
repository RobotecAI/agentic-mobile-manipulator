#!/usr/bin/env python3

import time

# generic ros libraries
import rclpy
from rclpy.logging import get_logger

# moveit python library
from moveit.planning import (
    MoveItPy,
    PlanningComponent,
)
from ament_index_python import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from moveit.utils import create_params_file_from_dict

from typing import List, cast

import rclpy
import time
import streamlit as st
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from typing import Type
from rai import get_llm_model
from rai.agents.langchain import (
    ReActAgent,
    ReActAgentState,
)
from rai.communication.ros2 import ROS2Connector
from rai.frontend.streamlit import run_streamlit_app
from rai.tools.ros2 import (
    GetROS2TransformConfiguredTool,
    GetROS2TransformTool,
    NavigateToPoseTool,
)
from rai.tools.time import WaitForSecondsTool

from rai_whoami import EmbodimentInfo
from geometry_msgs.msg import PoseStamped
import os

from typing import Literal, Type

import numpy as np
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from pydantic import BaseModel, Field

from nav2_simple_commander.robot_navigator import BasicNavigator
from tf2_geometry_msgs import do_transform_pose, do_transform_pose_stamped
from rclpy.action import ActionClient
from control_msgs.action import GripperCommand
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
            pose_stamped_msg=pose_stamped, pose_link=self.pose_link)

        plan = self.planning_component.plan()

        if plan:
            self.moveitpy.execute(plan.trajectory, controllers=[])
        else:
            return "Failed to plan the trajectory."

        return f"End effector successfully positioned at coordinates ({x:.2f}, {y:.2f}, {z:.2f})."

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
        orientation=Quaternion(
            x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)
        ),
    )
    poseWithTimestamp.header.frame_id = "map"
    navigator.goToPose(poseWithTimestamp)
    while not navigator.isTaskComplete():
        time.sleep(0.1)
    print("Going to pose successful")

def main(args=None):
    rclpy.init()

    moveit_config = (MoveItConfigsBuilder("rbkairos", package_name="robotec_kairos_ur10")
        .moveit_cpp(file_path=get_package_share_directory("robotec_kairos_ur10") + "/config/moveit_cpp.yaml")
        .robot_description(
            mappings={
                "namespace": f"ego",
                "prefix": f"ego",
                "ur_type": "ur10",
                "gazebo_classic": "false",
                "gazebo_ignition": "false",
            }
        )
        .robot_description_semantic(
            mappings={
                "namespace": f"ego",
                "prefix": f"ego",
            }
        )
        .to_moveit_configs().to_dict()
    )
    moveit_config.update({"use_sim_time": True})
    file = create_params_file_from_dict(moveit_config, "/**")

    moveitpy = MoveItPy(
        node_name="moveit_py",
        launch_params_filepaths=[file],
    )

    planning_component = moveitpy.get_planning_component("base")

    connector = ROS2Connector(executor_type="multi_threaded")
    manipulator_tool = MoveToPointTool(manipulator_frame="egoarm_base_link", pose_link="egoarm_wrist_3_link", moveitpy=moveitpy, planning_component=planning_component)

    gripper_action_client = ActionClient(connector._node, GripperCommand, "gripper_server")

    navigate_to_pose(
        x=2.608,
        y=2.739,
        z=0.0,
        yaw=180.0
    )

    def gripper_command(position):
        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 0.0
        future = gripper_action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(connector._node, future)
        if future.result() is None:
            raise RuntimeError("Gripper command failed")

    def pickup_object(object_frame):
        ros2_pose = do_transform_pose(
            Pose(),
            connector.get_transform(object_frame + "odom", object_frame),
        )
        ros2_pose = do_transform_pose(
            ros2_pose, connector.get_transform("egoarm_base_link", "odom")
        ).position

        result = None
        while result is None or not result.startswith("End effector successfully positioned"):
            result = manipulator_tool._run(x=ros2_pose.x, y=ros2_pose.y, z=(ros2_pose.z+0.03))

        time.sleep(1)

        gripper_command(0.0)

        result = None
        while result is None or not result.startswith("End effector successfully positioned"):
            result = manipulator_tool._run(x=ros2_pose.x, y=ros2_pose.y, z=(ros2_pose.z+0.3))

        time.sleep(1)

        gripper_command(1.0)
    
    for object_frame in ["carrot/", "blue_cube/", "apple/", "tomato/", "corn/", "red_cube/", "yellow_cube/", "green_cube/"]:
        pickup_object(object_frame)

if __name__ == "__main__":
    main()