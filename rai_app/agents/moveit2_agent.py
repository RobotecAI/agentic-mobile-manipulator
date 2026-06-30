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

import argparse
import logging
from pathlib import Path

import rclpy
from ament_index_python import get_package_share_directory
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.language_models.chat_models import BaseChatModel

# generic ros libraries
from langchain_core.language_models.fake_chat_models import FakeChatModel
from launch_param_builder import load_yaml
from moveit.core.kinematic_constraints import construct_joint_constraint
from moveit.core.planning_interface import MotionPlanResponse
from moveit.core.robot_state import RobotState
from moveit.planning import MoveItPy
from moveit.utils import create_params_file_from_dict
from moveit_configs_utils import MoveItConfigsBuilder
from rai.agents import wait_for_shutdown
from rai.agents.base import BaseAgent
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
)
from rai_interfaces.srv import MoveArm, SetArmJoints
from rclpy.action.client import ActionClient
from rclpy.node import Node
from tf2_geometry_msgs import do_transform_pose

from rai_app.control.moveit_utils import decode_error_code
from rai_app.initialization.llms import get_llm_model

GRIPPER_HEIGHT = 0.07


class MoveitToolkit:
    quaternion = Quaternion(x=0.9238795325112867, y=-0.3826834323650898, z=0.0, w=0.0)

    def __init__(self, namespace: str, ros_package_name) -> None:
        self.namespace = namespace
        self.ros_package_name = ros_package_name
        self.pose_link = f"{self.namespace}egoarm_wrist_3_link"
        self.manipulator_frame = f"{self.namespace}egoarm_base_link"
        self.moveitpy = self.setup_moveitpy()

        self.planning_component = self.moveitpy.get_planning_component("base")

    def setup_moveitpy(self) -> MoveItPy:
        package_config_dir = (
            Path(get_package_share_directory(self.ros_package_name)) / "config"
        )
        joint_limits_yaml_path = package_config_dir / "joint_limits.yaml"
        moveit_controllers_yaml_path = package_config_dir / "moveit_controllers.yaml"
        moveit_cpp_conf = package_config_dir / "moveit_cpp.yaml"
        trajectory_execution_conf = package_config_dir / "moveit_controllers.yaml"

        for path in [
            joint_limits_yaml_path,
            moveit_controllers_yaml_path,
            moveit_cpp_conf,
            trajectory_execution_conf,
        ]:
            if not path.exists():
                raise FileNotFoundError(f"File {path} doesn't exist")

        moveit_config = (
            MoveItConfigsBuilder("rbkairos", package_name=self.ros_package_name)
            .moveit_cpp(file_path=str(moveit_cpp_conf))
            .robot_description(
                mappings={
                    "namespace": f"{self.namespace}ego",
                    "prefix": f"{self.namespace}ego",
                    "ur_type": "ur10",
                    "gazebo_classic": "false",
                    "gazebo_ignition": "false",
                }
            )
            .trajectory_execution(
                file_path=str(trajectory_execution_conf),
                moveit_manage_controllers=False,
            )
            .robot_description_semantic(
                mappings={
                    "namespace": f"{self.namespace}ego",
                    "prefix": f"{self.namespace}ego",
                }
            )
            .to_moveit_configs()
        )

        joint_limits_params = self._get_joint_limit_params(joint_limits_yaml_path)
        moveit_controllers_params = self._get_moveit_controller_params(
            moveit_controllers_yaml_path
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
            remappings={"/joint_states": f"/{self.namespace}joint_states"},
        )

        return moveitpy

    def plan_and_execute(self, pose: Pose):
        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = self.manipulator_frame
        pose_stamped.pose = pose

        self.planning_component.set_start_state_to_current_state()
        self.planning_component.set_goal_state(
            pose_stamped_msg=pose_stamped, pose_link=self.pose_link
        )

        plan: MotionPlanResponse = self.planning_component.plan()
        if plan:
            self.moveitpy.execute(plan.trajectory, controllers=[])
        else:
            error_code = plan.error_code
            error_msg = decode_error_code(error_code)
            raise RuntimeError(f"Failed to plan the trajectory: {error_msg}")

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
            error_code = plan.error_code
            error_msg = decode_error_code(error_code)
            raise RuntimeError(f"Failed to plan the trajectory: {error_msg}")

    def _get_joint_limit_params(self, joint_limits_yaml_path: Path) -> dict:
        joint_limits_params = load_yaml(joint_limits_yaml_path)

        for joint in list(joint_limits_params["joint_limits"]):
            joint_limits_params["joint_limits"][f"{self.namespace}{joint}"] = (
                joint_limits_params["joint_limits"].pop(joint)
            )
        return joint_limits_params

    def _get_moveit_controller_params(self, moveit_controllers_yaml_path: Path) -> dict:
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
            params["joints"] = [
                f"{self.namespace}{joint}" for joint in params["joints"]
            ]
            moveit_controllers_params["moveit_simple_controller_manager"][
                f"{self.namespace}{controller}"
            ] = params
        moveit_controllers_params["moveit_simple_controller_manager"][
            "controller_names"
        ] = [f"{self.namespace}{controller}" for controller in controller_names]
        return moveit_controllers_params


class GripperController(Node):
    def __init__(self, namespace: str) -> None:
        super().__init__("gripper_controller")
        self.gripper_action_client = ActionClient(
            self, GripperCommand, f"{namespace}gripper_server"
        )
        pass

    def gripper_command(self, position):
        """Send a command to open or close the gripper.

        Parameters
        ----------
        position : float
            Target gripper position where ``0.0`` closes the gripper and ``1.0``
            opens it.

        Raises
        ------
        RuntimeError
            If the action server fails to execute the goal.
        """
        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 0.0
        future = self.gripper_action_client.send_goal_async(goal)

        # TODO(boczekbartek): fix this
        rclpy.spin_until_future_complete(self, future)
        if future.result() is None:
            raise RuntimeError("Gripper command failed")

    def close_gripper(self):
        self.gripper_command(0.0)

    def open_gripper(self):
        self.gripper_command(1.0)


class ArmController:
    ARM_STAGING_POSE_DISTANCE = 0.1
    BASE_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -1.5223139524459839,
        "egoarm_wrist_2_joint": -1.5707021951675415,
        "egoarm_wrist_3_joint": -0.841789960861206,
        "egoarm_shoulder_lift_joint": -2.226045608520508,
        "egoarm_elbow_joint": 2.1977827548980713,
        "egoarm_shoulder_pan_joint": 0.018245616927742958,
    }

    LOW_BASE_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -2.150108575820923,
        "egoarm_wrist_2_joint": -1.5708777904510498,
        "egoarm_wrist_3_joint": -0.84187912940979,
        "egoarm_shoulder_lift_joint": -0.06665489822626114,
        "egoarm_elbow_joint": 0.6900210380554199,
        "egoarm_shoulder_pan_joint": 0.018179576843976974,
    }

    def __init__(
        self, connector: ROS2Connector, namespace: str, ros_package_name: str
    ) -> None:
        self.connector = connector
        self.namespace = namespace
        self.ros_package_name = ros_package_name

        self.logger = logging.getLogger(__name__)

        self.moveit_toolkit = MoveitToolkit(namespace, ros_package_name)

    def move_arm(self, pose: Pose, frame: str | None = None, retries: int = 3):
        if frame is None:
            frame = f"{self.namespace}egoarm_base_link"
        ros2_pose = do_transform_pose(
            pose,
            self.connector.get_transform(
                f"{self.namespace}egoarm_base_link", frame, timeout_sec=60
            ),
        )

        self.logger.info(
            f"Moving arm to {ros2_pose.position.x}, {ros2_pose.position.y}, {ros2_pose.position.z}"
        )
        for _ in range(retries):
            try:
                self.moveit_toolkit.plan_and_execute(ros2_pose)
                return True
            except RuntimeError as e:
                self.logger.error(e)
                continue
        raise RuntimeError("Failed to move arm")

    def move_arm_to_base_pose(self):
        self.moveit_toolkit.set_joint_values(self.BASE_JOINT_VALUES)

    def move_arm_to_low_base_pose(self):
        self.moveit_toolkit.set_joint_values(self.LOW_BASE_JOINT_VALUES)

    def move_arm_to_staging_pose(self, target_pose: Pose, object_height: float):
        self.move_arm(
            Pose(
                position=Point(
                    x=target_pose.position.x,
                    y=target_pose.position.y,
                    z=target_pose.position.z
                    + object_height
                    + self.ARM_STAGING_POSE_DISTANCE,
                )
            ),
            "odom",
        )

    def move_arm_to_gripping_pose(self, target_pose: Pose, object_height: float):
        self.move_arm(
            Pose(
                position=Point(
                    x=target_pose.position.x,
                    y=target_pose.position.y,
                    z=target_pose.position.z + object_height,
                )
            ),
            "odom",
        )


class ManipulatorController:
    def __init__(
        self,
        connector: ROS2Connector,
        namespace: str = "",
        ros_package_name: str = "robotec_kairos_ur10",
    ) -> None:
        self.ros_package_name = ros_package_name
        self.connector = connector
        self.node = self.connector.node
        self.namespace = namespace

        self.logger = self.node.get_logger()

        self.gripper_controller = GripperController(self.namespace)
        self.arm_controller = ArmController(
            self.connector, self.namespace, self.ros_package_name
        )

    def open_gripper(self):
        self.gripper_controller.open_gripper()

    def close_gripper(self):
        self.gripper_controller.close_gripper()

    def move_arm(self, pose, frame: str | None = None):
        self.arm_controller.move_arm(pose, frame)

    def move_arm_to_base_pose(self):
        self.arm_controller.move_arm_to_base_pose()

    def move_arm_to_low_base_pose(self):
        self.arm_controller.move_arm_to_low_base_pose()

    def move_arm_to_staging_pose(self, target_pose: Pose, object_height: float):
        self.arm_controller.move_arm_to_staging_pose(target_pose, object_height)

    def move_arm_to_gripping_pose(self, target_pose: Pose, object_height: float):
        self.arm_controller.move_arm_to_gripping_pose(target_pose, object_height)


def logging_wrapper(func):
    def wrapper(self, *args, **kwargs):
        RED = "\033[91m"
        GREEN = "\033[92m"
        RESET = "\033[0m"
        self.connector.node.get_logger().info(
            f"{GREEN}Calling {func.__name__} with args: {args} and kwargs: {kwargs}{RESET}"
        )
        result = func(self, *args, **kwargs)
        color = GREEN if result.success else RED
        msg = f"{color}Result of {func.__name__}: success={result.success}{RESET}"
        msg += f" {result.report}" if not result.success else ""
        self.connector.node.get_logger().info(msg)
        return result

    return wrapper


class MoveIt2Agent(BaseAgent):
    SYSTEM_PROMPT: str = """
    You are an agent responsible for moving the robotic arm to a specified position and gripper state.
    You work alongside other agents and specialists to accomplish the task.
    You work within the MoveIt2, ROS 2 framework.
    When asked to debug, check the logs and provide short and actionable summary for the other agents.
    """

    def __init__(self, llm: BaseChatModel | None = None):
        super().__init__()
        self.connector = ROS2Connector(executor_type="single_threaded")
        self.manipulator_controller = ManipulatorController(
            connector=self.connector,
            namespace="",
            ros_package_name="robotec_kairos_ur10",
        )

        if llm is None:
            self.llm = FakeChatModel()
        else:
            self.llm = llm

        self.connector.create_service(
            service_name="/rai/moveit2/move_arm",
            service_type="rai_interfaces/srv/MoveArm",
            on_request=self.move_arm,
        )
        self.connector.create_service(
            service_name="/rai/moveit2/set_arm_joints",
            service_type="rai_interfaces/srv/SetArmJoints",
            on_request=self.set_arm_joints,
        )

        self.logger.info("MoveIt2Agent initialized")

    def formulate_prompt(self, prompt: str, logs: str) -> str:
        return self.SYSTEM_PROMPT + "\n\n Task:\n" + prompt + "\n\n Logs:\n" + logs

    @logging_wrapper
    def set_arm_joints(
        self, request: SetArmJoints.Request, response: SetArmJoints.Response
    ):
        self.logger.info(
            f"Setting arm joints: {request.joints_names} to {request.joints}"
        )
        try:
            joints = {k: v for k, v in zip(request.joints_names, request.joints)}
            self.manipulator_controller.arm_controller.moveit_toolkit.set_joint_values(
                joints
            )
            response.success = True
            response.report = "Moved arm to position."
            return response
        except Exception as e:
            self.logger.error(f"Failed to set arm joints: {e}")
            response.success = False
            response.report = str(e)
        return response

    def _is_neutral_pose(self, pose: PoseStamped) -> bool:
        neutral_pose = PoseStamped().pose
        test_pose = pose.pose
        return (
            test_pose.position.x == neutral_pose.position.x
            and test_pose.position.y == neutral_pose.position.y
            and test_pose.position.z == neutral_pose.position.z
            and test_pose.orientation.x == neutral_pose.orientation.x
            and test_pose.orientation.y == neutral_pose.orientation.y
            and test_pose.orientation.z == neutral_pose.orientation.z
            and test_pose.orientation.w == neutral_pose.orientation.w
        )

    @logging_wrapper
    def move_arm(self, request: MoveArm.Request, response: MoveArm.Response):
        if not self._is_neutral_pose(
            request.target_pose
        ):  # empty pose, gripper state only
            try:
                self.manipulator_controller.move_arm(
                    pose=request.target_pose.pose,
                    frame=request.target_pose.header.frame_id,
                )
            except Exception as e:
                response.success = False
                try:
                    llm_response = self.llm.invoke(
                        "The arm failed to move to the position. Check the logs and provide a short summary."
                        + str(e)
                    )
                    response.report = llm_response.content
                except Exception:
                    response.report = f"The arm failed to move to the position: {e}"
                return response

        if request.gripper_state == 0:
            response.success = True
            response.report = "Moved arm to position."
        elif request.gripper_state == 1:
            try:
                self.manipulator_controller.open_gripper()
                response.success = True
                response.report = "Moved arm to position and opened gripper."
            except Exception as e:
                self.logger.error(f"Failed to open gripper: {e}")
                response.success = False
                try:
                    llm_response = self.llm.invoke(
                        self.formulate_prompt("The arm failed to open the gripper.", str(e))
                    )
                    response.report = llm_response.content
                except Exception:
                    response.report = f"The arm failed to open the gripper: {e}"
                return response
        elif request.gripper_state == 2:
            try:
                self.manipulator_controller.close_gripper()
                response.success = True
                response.report = "Moved arm to position and closed gripper."
            except Exception as e:
                self.logger.error(f"Failed to close gripper: {e}")
                response.success = False
                try:
                    llm_response = self.llm.invoke(
                        self.formulate_prompt(
                            "The arm failed to close the gripper.", str(e)
                        )
                    )
                    response.report = llm_response.content
                except Exception:
                    response.report = f"The arm failed to open the gripper: {e}"
                return response
        else:
            response.success = False
            response.report = "Invalid gripper state."
        return response

    def run(self):
        pass

    def stop(self):
        self.connector.shutdown()


@ROS2Context()
def main():
    parser = argparse.ArgumentParser(description="Run MoveIt2 agent")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    args = parser.parse_args()
    if args.test_mode:
        llm = FakeChatModel()
    else:
        llm = get_llm_model(config_name="general")
    agent = MoveIt2Agent(llm=llm)
    agent.run()

    wait_for_shutdown([agent])


if __name__ == "__main__":
    main()
