import time
from pathlib import Path

# generic ros libraries
import rclpy
from ament_index_python import get_package_share_directory
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from launch_param_builder import load_yaml
from moveit.core.kinematic_constraints import construct_joint_constraint
from moveit.core.planning_interface import MotionPlanResponse
from moveit.core.robot_state import RobotState
from moveit.planning import MoveItPy
from moveit.utils import create_params_file_from_dict
from moveit_configs_utils import MoveItConfigsBuilder
from rai.communication.ros2 import ROS2Connector
from rclpy.action.client import ActionClient
from rclpy.node import Node
from tf2_geometry_msgs import do_transform_pose

from scripts.moveit_utils import decode_error_code


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

        print(dir(MoveItPy))
        moveitpy = MoveItPy(
            node_name="moveit_py",
            launch_params_filepaths=[file],
            remappings={"/joint_states": f"/{self.namespace}joint_states"},
        )

        return moveitpy

    def plan_and_execute(self, x, y, z):
        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = self.manipulator_frame
        pose_stamped.pose = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=self.quaternion,
        )

        print("Setting to start_state_to_current_state", flush=True)
        self.planning_component.set_start_state_to_current_state()
        print("Set goal state", flush=True)
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
        """
        position = 0.0 - close the gripper
        position = 1.0 - open the gripper
        """
        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = 0.0
        future = self.gripper_action_client.send_goal_async(goal)

        # TODO(boczekbartek): fix this
        rclpy.spin_until_future_complete(self, future)
        if future.result() is None:
            raise RuntimeError("Gripper command failed")

        time.sleep(1)

    def close_gripper(self):
        self.gripper_command(0.0)

    def open_gripper(self):
        self.gripper_command(1.0)


class ArmController:
    ARM_STAGING_POSE_DISTANCE = 0.2
    BASE_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -1.5223139524459839,
        "egoarm_wrist_2_joint": -1.5707021951675415,
        "egoarm_wrist_3_joint": -0.841789960861206,
        "egoarm_shoulder_lift_joint": -2.226045608520508,
        "egoarm_elbow_joint": 2.1977827548980713,
        "egoarm_shoulder_pan_joint": 0.018245616927742958,
    }

    def __init__(
        self, connector: ROS2Connector, namespace: str, ros_package_name: str
    ) -> None:
        self.connector = connector
        self.namespace = namespace
        self.ros_package_name = ros_package_name
        import logging

        self.logger = logging.getLogger(__name__)
        # self.node.get_logger()

        self.moveit_toolkit = MoveitToolkit(namespace, ros_package_name)

    def move_arm(self, pose, frame: str | None = None, retries: int = 3):
        if frame is None:
            frame = f"{self.namespace}egoarm_base_link"
        ros2_pose = do_transform_pose(
            pose,
            self.connector.get_transform(
                f"{self.namespace}egoarm_base_link", frame, timeout_sec=60
            ),
        ).position

        self.logger.info(f"Moving arm to {ros2_pose.x}, {ros2_pose.y}, {ros2_pose.z}")
        for _ in range(retries):
            try:
                self.moveit_toolkit.plan_and_execute(
                    x=ros2_pose.x, y=ros2_pose.y, z=(ros2_pose.z)
                )
                break
            except RuntimeError as e:
                self.logger.error(e)

        time.sleep(1)

    def move_arm_to_base_pose(self):
        self.moveit_toolkit.set_joint_values(self.BASE_JOINT_VALUES)

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
        self, connector: ROS2Connector, namespace: str, ros_package_name: str
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

    def move_arm_to_staging_pose(self, target_pose: Pose, object_height: float):
        self.arm_controller.move_arm_to_staging_pose(target_pose, object_height)

    def move_arm_to_gripping_pose(self, target_pose: Pose, object_height: float):
        self.arm_controller.move_arm_to_gripping_pose(target_pose, object_height)
