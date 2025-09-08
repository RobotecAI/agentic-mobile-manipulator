#!/usr/bin/env python3

import os
import time
from pathlib import Path
from typing import Type

import numpy as np

# generic ros libraries
import rclpy
from ament_index_python import get_package_share_directory
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.tools import BaseTool
from launch_param_builder import load_yaml

# moveit python library
from moveit.planning import (
    MoveItPy,
    PlanningComponent,
)
from moveit.utils import create_params_file_from_dict
from moveit_configs_utils import MoveItConfigsBuilder
from nav2_simple_commander.robot_navigator import BasicNavigator
from pydantic import BaseModel, Field
from rai.communication.ros2 import ROS2Connector
from rclpy.action import ActionClient
from rclpy.node import Node
from tf2_geometry_msgs import do_transform_pose


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


def navigate_to_pose(
    x: float,
    y: float,
    z: float = 0.0,
    yaw: float = 0.0,
    frame: str = "map",
):
    navigator = BasicNavigator()
    poseWithTimestamp = PoseStamped()
    poseWithTimestamp.pose = Pose(
        position=Point(x=x, y=y, z=z),
        orientation=Quaternion(x=0.0, y=0.0, z=np.sin(yaw / 2), w=np.cos(yaw / 2)),
    )
    poseWithTimestamp.header.frame_id = frame
    navigator.goToPose(poseWithTimestamp)
    while not navigator.isTaskComplete():
        time.sleep(0.1)
    print("Going to pose successful")

    time.sleep(1)


def main(args=None):
    rclpy.init()

    namespace_value = ""

    joint_limits_yaml_path = get_package_share_directory("robotec_kairos_ur10")
    joint_limits_yaml_path = os.path.join(
        joint_limits_yaml_path, "config", "joint_limits.yaml"
    )
    joint_limits_params = load_yaml(Path(joint_limits_yaml_path))
    for joint in list(joint_limits_params["joint_limits"]):
        joint_limits_params["joint_limits"][f"{namespace_value}{joint}"] = (
            joint_limits_params["joint_limits"].pop(joint)
        )

    moveit_controllers_yaml_path = get_package_share_directory("robotec_kairos_ur10")
    moveit_controllers_yaml_path = os.path.join(
        moveit_controllers_yaml_path, "config", "moveit_controllers.yaml"
    )
    moveit_controllers_params = load_yaml(Path(moveit_controllers_yaml_path))
    controller_names = list(
        moveit_controllers_params["moveit_simple_controller_manager"][
            "controller_names"
        ]
    )
    for controller in controller_names:
        params = moveit_controllers_params["moveit_simple_controller_manager"].pop(
            controller
        )
        params["joints"] = [f"{namespace_value}{joint}" for joint in params["joints"]]
        moveit_controllers_params["moveit_simple_controller_manager"][
            f"{namespace_value}{controller}"
        ] = params
    moveit_controllers_params["moveit_simple_controller_manager"][
        "controller_names"
    ] = [f"{namespace_value}{controller}" for controller in controller_names]

    moveit_config = (
        MoveItConfigsBuilder("rbkairos", package_name="robotec_kairos_ur10")
        .moveit_cpp(
            file_path=get_package_share_directory("robotec_kairos_ur10")
            + "/config/moveit_cpp.yaml"
        )
        .robot_description(
            mappings={
                "namespace": f"{namespace_value}ego",
                "prefix": f"{namespace_value}ego",
                "ur_type": "ur10",
                "gazebo_classic": "false",
                "gazebo_ignition": "false",
            }
        )
        .trajectory_execution(
            file_path=get_package_share_directory("robotec_kairos_ur10")
            + "/config/moveit_controllers.yaml",
            moveit_manage_controllers=False,
        )
        .robot_description_semantic(
            mappings={
                "namespace": f"{namespace_value}ego",
                "prefix": f"{namespace_value}ego",
            }
        )
        .to_moveit_configs()
    )
    moveit_config.joint_limits = {"robot_description_planning": joint_limits_params}
    moveit_config = moveit_config.to_dict()
    moveit_config.update({"use_sim_time": True})
    file = create_params_file_from_dict(
        moveit_config | moveit_controllers_params, "/**"
    )

    moveitpy = MoveItPy(
        node_name="moveit_py",
        launch_params_filepaths=[file],
        remappings={"/joint_states": f"/{namespace_value}joint_states"},
    )

    planning_component = moveitpy.get_planning_component("base")

    connector = ROS2Connector(executor_type="multi_threaded")
    manipulator_tool = MoveToPointTool(
        manipulator_frame=f"{namespace_value}egoarm_base_link",
        pose_link=f"{namespace_value}egoarm_wrist_3_link",
        moveitpy=moveitpy,
        planning_component=planning_component,
    )

    node = Node("gripper_action_client_node")

    gripper_action_client = ActionClient(
        node, GripperCommand, f"{namespace_value}gripper_server"
    )

    def move_arm(pose, frame):
        ros2_pose = do_transform_pose(
            pose,
            connector.get_transform(
                f"{namespace_value}egoarm_base_link", frame, timeout_sec=60
            ),
        ).position

        print(f"Moving to {ros2_pose.x}, {ros2_pose.y}, {ros2_pose.z}")
        result = None
        while result is None or not result.startswith(
            "End effector successfully positioned"
        ):
            result = manipulator_tool._run(
                x=ros2_pose.x, y=ros2_pose.y, z=(ros2_pose.z)
            )

        time.sleep(1)

    def gripper_command(position):
        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 0.0
        future = gripper_action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future)
        if future.result() is None:
            raise RuntimeError("Gripper command failed")

        time.sleep(1)

    def get_object_height(object_name):
        gripping_point_pose = do_transform_pose(
            Pose(),
            connector.get_transform(
                f"{object_name}/gripping_point", f"{object_name}/base_link_gt"
            ),
        ).position

        return np.abs(gripping_point_pose.z)

    def get_slot_height(slot_frame):
        slot_pose = do_transform_pose(
            Pose(),
            connector.get_transform(f"{namespace_value}egoarm_base_link", slot_frame),
        ).position

        return slot_pose.z

    def move_back():
        navigator = BasicNavigator()
        navigator.driveOnHeading(-1.0, -0.4)
        while not navigator.isTaskComplete():
            time.sleep(0.1)
        print("Going to pose successful")

        time.sleep(1)

    def place_object_on_rack(object_name, slot_number):
        object_frame = f"{object_name}/gripping_point"

        navigate_to_pose(x=0.0, y=-0.7, yaw=np.pi / 2, frame=object_frame)

        move_arm(Pose(position=Point(z=0.2)), object_frame)
        move_arm(Pose(), object_frame)

        gripper_command(0.0)

        move_arm(Pose(position=Point(z=0.2)), object_frame)
        move_arm(
            Pose(position=Point(x=0.6, z=0.8)), f"{namespace_value}egoarm_base_link"
        )

        slot_frame = f"rack_slot{slot_number}"
        navigate_to_pose(x=-2.0, y=0.0, frame=slot_frame)

        slot_height = get_slot_height(slot_frame)
        object_height = get_object_height(object_name)
        move_arm(
            Pose(position=Point(x=0.6, z=slot_height + object_height + 0.2)),
            f"{namespace_value}egoarm_base_link",
        )
        navigate_to_pose(x=-0.7, y=0.0, frame=slot_frame)

        move_arm(Pose(position=Point(x=0.0, y=0.0, z=object_height)), slot_frame)

        gripper_command(1.0)

        move_arm(
            Pose(position=Point(x=0.6, z=slot_height + object_height + 0.2)),
            f"{namespace_value}egoarm_base_link",
        )

        move_back()

    slot_number = 1
    for object_name in [
        "CardboardBox01",
        "CardboardBoxDamaged01",
        "CardboardBoxDamaged02",
        "CardboardBox02",
    ]:
        place_object_on_rack(object_name, slot_number)
        slot_number += 1


if __name__ == "__main__":
    main()
