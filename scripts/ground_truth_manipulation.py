#!/usr/bin/env python3

import csv
import os
import time
from io import StringIO
from pathlib import Path
from typing import Type

import numpy as np

# generic ros libraries
import rclpy
from ament_index_python import get_package_share_directory
from anomalies import Spawn, poses_raw
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.tools import BaseTool
from launch_param_builder import load_yaml
from moveit.core.kinematic_constraints import construct_joint_constraint
from moveit.core.robot_state import RobotState

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
from simulation_interfaces.srv import GetEntityState
from tf2_geometry_msgs import TransformStamped, do_transform_pose

NAV_GRIPPING_POSE_DISTANCE = 0.80
NAV_STAGING_POSE_DISTANCE = 1.0
ARM_STAGING_POSE_DISTANCE = 0.2
BASE_JOINT_VALUES = {
    "egoarm_wrist_1_joint": -1.5223139524459839,
    "egoarm_wrist_2_joint": -1.5707021951675415,
    "egoarm_wrist_3_joint": -0.841789960861206,
    "egoarm_shoulder_lift_joint": -2.226045608520508,
    "egoarm_elbow_joint": 2.1977827548980713,
    "egoarm_shoulder_pan_joint": 0.018245616927742958,
}


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

    node = Node("ground_truth_manipulation")

    gripper_action_client = ActionClient(
        node, GripperCommand, f"{namespace_value}gripper_server"
    )

    def move_arm(pose, frame=f"{namespace_value}egoarm_base_link"):
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

    # Retrieve the pose of an entity in a specified frame
    def get_pose(entity_name, frame="odom"):
        client_getState = node.create_client(GetEntityState, "get_entity_state")

        while not client_getState.wait_for_service(timeout_sec=1.0):
            node.get_logger().error(
                "Service get_entity_state not available, waiting..."
            )

        req_get = GetEntityState.Request()
        req_get.entity = entity_name
        future_get = client_getState.call_async(req_get)
        rclpy.spin_until_future_complete(node, future_get)
        if future_get.result() is not None:
            entity_state = future_get.result().state
            print(f"Entity state: {entity_state}")
        else:
            node.get_logger().error(f"Service call failed: {future_get.exception()}")
            return

        return do_transform_pose(
            entity_state.pose,
            connector.get_transform(frame, "odom"),
        )

    # Given a local pose and an origin pose, return the global pose
    def get_global_pose_from_origin(local_pose: Pose, origin: Pose):
        transform = TransformStamped()
        transform.header.frame_id = "odom"
        transform.transform.translation.x = origin.position.x
        transform.transform.translation.y = origin.position.y
        transform.transform.translation.z = origin.position.z
        transform.transform.rotation = origin.orientation
        return do_transform_pose(pose=local_pose, transform=transform)

    # Given a local pose and an entity name, return the global pose of that entity
    def get_global_pose(local_pose: Pose, entity_name: str):
        entity_pose = get_pose(entity_name)
        return get_global_pose_from_origin(local_pose, entity_pose)

    # Calculate the height of an object's gripping point based on its base
    def get_object_height(object_name):
        object_pose = get_pose(object_name)
        gripping_point_pose = get_pose(f"{object_name}_GrippingPoint")

        return np.abs(gripping_point_pose.position.z - object_pose.position.z)

    # position = 0.0 - close the gripper
    # position = 1.0 - open the gripper
    def gripper_command(position):
        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 0.0
        future = gripper_action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future)
        if future.result() is None:
            raise RuntimeError("Gripper command failed")

        time.sleep(1)

    def close_gripper():
        gripper_command(0.0)

    def open_gripper():
        gripper_command(1.0)

    # Move the robot backward by a specified distance using driveOnHeading
    def move_back(dist=0.2):
        navigator = BasicNavigator()
        navigator.driveOnHeading(-dist, -0.4)
        while not navigator.isTaskComplete():
            time.sleep(0.1)
        print("Going to pose successful")

        time.sleep(1)

    def navigate_to_staging_pose(target_pose: Pose):
        nav_staging_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_STAGING_POSE_DISTANCE)), target_pose
        )
        navigate_to_pose(
            nav_staging_pose.position,
            yaw=get_lookat_yaw(nav_staging_pose.position, target_pose.position),
        )

    def navigate_to_gripping_pose(target_pose: Pose):
        nav_gripping_pose = get_global_pose_from_origin(
            Pose(position=Point(x=-NAV_GRIPPING_POSE_DISTANCE)), target_pose
        )
        navigate_to_pose(
            nav_gripping_pose.position,
            yaw=get_lookat_yaw(nav_gripping_pose.position, target_pose.position),
        )

    def move_arm_to_staging_pose(target_pose: Pose, object_height: float):
        move_arm(
            Pose(
                position=Point(
                    x=target_pose.position.x,
                    y=target_pose.position.y,
                    z=target_pose.position.z
                    + object_height
                    + ARM_STAGING_POSE_DISTANCE,
                )
            ),
            "odom",
        )

    def move_arm_to_gripping_pose(target_pose: Pose, object_height: float):
        move_arm(
            Pose(
                position=Point(
                    x=target_pose.position.x,
                    y=target_pose.position.y,
                    z=target_pose.position.z + object_height,
                )
            ),
            "odom",
        )

    def move_arm_to_base_pose():
        manipulator_tool.set_joint_values(BASE_JOINT_VALUES)

    def place_object_on_rack(object_name, slot_pose):
        object_pose = get_pose(object_name)

        navigate_to_staging_pose(object_pose)
        navigate_to_gripping_pose(object_pose)

        object_height = get_object_height(object_name)

        move_arm_to_staging_pose(object_pose, object_height)
        move_arm_to_gripping_pose(object_pose, object_height)

        close_gripper()

        move_arm_to_staging_pose(object_pose, object_height)

        move_back()

        move_arm_to_base_pose()

        navigate_to_staging_pose(slot_pose)
        navigate_to_gripping_pose(slot_pose)

        move_arm_to_staging_pose(slot_pose, object_height)
        move_arm_to_gripping_pose(slot_pose, object_height)

        open_gripper()

        move_arm_to_staging_pose(slot_pose, object_height)
        move_arm_to_base_pose()

        move_back()

    slot_poses = {}
    reader = csv.reader(StringIO(poses_raw))
    for row in reader:
        if len(row) == 0:
            continue
        name = row[0]
        x, y, z, qx, qy, qz, qw = map(float, row[2:])
        slot_poses[name] = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=Quaternion(x=qx, y=qy, z=qz, w=qw),
        )

    entity_types = [
        "cardboardbox01",
        "cardboardbox02",
        "cardboardboxdamaged01",
        "cardboardboxdamaged02",
    ]
    spawn_entity_types = [entity_types[i % len(entity_types)] for i in range(16)]
    entity_names = [f"box{i}" for i in range(len(spawn_entity_types))]
    spawn_slot_names = [
        "I01/RackSlot1",
        "I01/RackSlot2",
        "I01/RackSlot5",
        "I01/RackSlot6",
        "H01/RackSlot1",
        "H01/RackSlot2",
        "H01/RackSlot5",
        "H01/RackSlot6",
        "t1/Slot5",
        "t1/Slot6",
        "t1/Slot7",
        "t1/Slot8",
        "t2/Slot5",
        "t2/Slot6",
        "t2/Slot7",
        "t2/Slot8",
    ]
    target_slot_names = [
        "t3/Slot1",
        "t3/Slot2",
        "t3/Slot3",
        "t3/Slot4",
        "t4/Slot1",
        "t4/Slot2",
        "t4/Slot3",
        "t4/Slot4",
        "C04/RackSlot1",
        "C04/RackSlot2",
        "C04/RackSlot5",
        "C04/RackSlot6",
        "B04/RackSlot1",
        "B04/RackSlot2",
        "B04/RackSlot5",
        "B04/RackSlot6",
    ]
    for entity_name, spawn_entity_type, spawn_slot_name in zip(
        entity_names, spawn_entity_types, spawn_slot_names
    ):
        Spawn(
            node,
            spawn_entity_type,
            entity_name,
            slot_poses[spawn_slot_name].position.x,
            slot_poses[spawn_slot_name].position.y,
            slot_poses[spawn_slot_name].position.z,
            slot_poses[spawn_slot_name].orientation.x,
            slot_poses[spawn_slot_name].orientation.y,
            slot_poses[spawn_slot_name].orientation.z,
            slot_poses[spawn_slot_name].orientation.w,
        )

    move_arm_to_base_pose()

    for entity_name, target_slot_name in zip(entity_names, target_slot_names):
        place_object_on_rack(entity_name, slot_poses[target_slot_name])


if __name__ == "__main__":
    main()
