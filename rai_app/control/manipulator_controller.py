from typing import Dict, Literal

import numpy as np
import tf_transformations
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from rai.communication.ros2 import ROS2Connector, ROS2Message

from rai_app.geometry_helpers import get_global_pose_from_origin

GRIPPER_HEIGHT = 0.07


class ManipulatorController:
    """High-level interface wrapping MoveIt-related arm and gripper actions."""

    ARM_STAGING_POSE_DISTANCE = 0.10
    TOP_GRASP_BASE_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -1.5200964212417603,
        "egoarm_wrist_2_joint": -1.5707420110702515,
        "egoarm_wrist_3_joint": 1.5707147121429443,
        "egoarm_shoulder_lift_joint": -2.223454713821411,
        "egoarm_elbow_joint": 2.2145509719848633,
        "egoarm_shoulder_pan_joint": 0.018249407410621643,
    }

    SIDE_GRASP_BASE_JOINT_VALUES = {
        "egoarm_wrist_1_joint": 0.35376831889152527,
        "egoarm_wrist_2_joint": 1.9237881898880005,
        "egoarm_wrist_3_joint": -1.5593433380126953,
        "egoarm_shoulder_lift_joint": -2.2522737979888916,
        "egoarm_elbow_joint": 1.9098111391067505,
        "egoarm_shoulder_pan_joint": 0.2729571461677551,
    }

    TOP_GRASP_LOW_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -2.847410202026367,
        "egoarm_wrist_2_joint": -1.5687670707702637,
        "egoarm_wrist_3_joint": 1.193854570388794,
        "egoarm_shoulder_lift_joint": -0.446782648563385,
        "egoarm_elbow_joint": 1.7715840339660645,
        "egoarm_shoulder_pan_joint": -0.3584860563278198,
    }

    SIDE_GRASP_HIGH_JOINT_VALUES = {
        "egoarm_wrist_1_joint": 0.972610354423523,
        "egoarm_wrist_2_joint": 0.8618453741073608,
        "egoarm_wrist_3_joint": -1.580148458480835,
        "egoarm_shoulder_lift_joint": -1.8791487216949463,
        "egoarm_elbow_joint": 0.9604578614234924,
        "egoarm_shoulder_pan_joint": -0.7146416306495667,
    }

    SIDE_GRASP_LOW_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -1.4295639991760254,
        "egoarm_wrist_2_joint": 1.2269102334976196,
        "egoarm_wrist_3_joint": -1.5503735542297363,
        "egoarm_shoulder_lift_joint": -0.38649436831474304,
        "egoarm_elbow_joint": 1.8341058492660522,
        "egoarm_shoulder_pan_joint": -0.3496033847332001,
    }

    # so that wrist camera is slightly higher and can view whole racks
    HOUSEKEEP_JOINT_VALUES = {
        "egoarm_wrist_1_joint": -1.7678067684173584,
        "egoarm_wrist_2_joint": -1.570849895477295,
        "egoarm_wrist_3_joint": 1.5707409381866455,
        "egoarm_shoulder_lift_joint": -2.2628884315490723,
        "egoarm_elbow_joint": 2.181567430496216,
        "egoarm_shoulder_pan_joint": 0.01814597100019455,
    }

    def __init__(
        self,
        connector: ROS2Connector | None = None,
    ):
        self.connector = connector or ROS2Connector(executor_type="single_threaded")
        upside_down_quat = tf_transformations.quaternion_from_euler(np.pi, 0, 0)
        self.upside_down_quat = Quaternion(
            x=upside_down_quat[0],
            y=upside_down_quat[1],
            z=upside_down_quat[2],
            w=upside_down_quat[3],
        )

        # By which face should the manipulator grasp the object
        self.grasp_type: Literal["top", "side"] = "top"

    def set_grasp_type(self, grasp_type: Literal["top", "side"]):
        self.grasp_type = grasp_type

    def open_gripper(self):
        response = self.connector.service_call(
            message=ROS2Message(payload={"gripper_state": 1}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
        if response.payload is None:
            raise RuntimeError("Failed to open gripper: no response from the service")
        if not response.payload.success:
            raise RuntimeError(f"Failed to open gripper: {response.payload.report}")
        return response

    def close_gripper(self):
        response = self.connector.service_call(
            message=ROS2Message(payload={"gripper_state": 2}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
        if response.payload is None:
            raise RuntimeError("Failed to close gripper: no response from the service")
        if not response.payload.success:
            raise RuntimeError(f"Failed to close gripper: {response.payload.report}")
        return response

    def move_arm(self, pose: PoseStamped):
        response = self.connector.service_call(
            message=ROS2Message(payload={"target_pose": pose}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
        if response.payload is None:
            raise RuntimeError("Failed to move arm: no response from the service")
        if not response.payload.success:
            raise RuntimeError(f"Failed to move arm: {response.payload.report}")
        return response

    def set_arm_joints(self, joints: Dict[str, float]):
        joints_values = list(joints.values())
        joints_names = list(joints.keys())
        response = self.connector.service_call(
            message=ROS2Message(
                payload={"joints": joints_values, "joints_names": joints_names}
            ),
            target="/rai/moveit2/set_arm_joints",
            msg_type="rai_interfaces/srv/SetArmJoints",
        )
        if response.payload is None:
            raise RuntimeError("Failed to set arm joints: no response from the service")
        if not response.payload.success:
            raise RuntimeError(f"Failed to set arm joints: {response.payload.report}")
        return response

    def move_arm_to_base_pose(self):
        if self.grasp_type == "top":
            return self.set_arm_joints(self.TOP_GRASP_BASE_JOINT_VALUES)
        elif self.grasp_type == "side":
            return self.set_arm_joints(self.SIDE_GRASP_BASE_JOINT_VALUES)

    def move_arm_to_rack_view_pose(self):
        return self.set_arm_joints(self.HOUSEKEEP_JOINT_VALUES)

    def move_arm_to_staging_pose(self, target_pose: Pose):
        calculated_pose = PoseStamped()
        calculated_pose.pose = get_global_pose_from_origin(
            Pose(
                position=Point(
                    x=0.0,
                    y=0.0,
                    z=GRIPPER_HEIGHT + self.ARM_STAGING_POSE_DISTANCE,
                ),
                orientation=self.upside_down_quat,
            ),
            target_pose,
        )
        calculated_pose.header.frame_id = "odom"
        return self.move_arm(calculated_pose)

    def move_arm_to_target_pose(self, target_pose: Pose):
        calculated_pose = PoseStamped()
        calculated_pose.pose = get_global_pose_from_origin(
            Pose(
                position=Point(
                    x=0.0,
                    y=0.0,
                    z=GRIPPER_HEIGHT,
                ),
                orientation=self.upside_down_quat,
            ),
            target_pose,
        )
        calculated_pose.header.frame_id = "odom"
        return self.move_arm(calculated_pose)

    def move_arm_to_low_pose(self):
        if self.grasp_type == "top":
            return self.set_arm_joints(self.TOP_GRASP_LOW_JOINT_VALUES)
        elif self.grasp_type == "side":
            return self.set_arm_joints(self.SIDE_GRASP_LOW_JOINT_VALUES)

    def move_arm_to_high_pose(self):
        if self.grasp_type == "top":
            raise ValueError(
                "Top grasp is not supported in high pose, set grasp_type to side!"
            )
        elif self.grasp_type == "side":
            return self.set_arm_joints(self.SIDE_GRASP_HIGH_JOINT_VALUES)

    def move_arm_to_above_target_pose(self, target_pose: Pose):
        above_target_pose = Pose(
            position=Point(
                x=target_pose.position.x,
                y=target_pose.position.y,
                z=target_pose.position.z + self.ARM_STAGING_POSE_DISTANCE,
            ),
            orientation=target_pose.orientation,
        )
        calculated_pose = PoseStamped()
        calculated_pose.pose = get_global_pose_from_origin(
            Pose(
                position=Point(
                    x=0.0,
                    y=0.0,
                    z=GRIPPER_HEIGHT,
                ),
                orientation=self.upside_down_quat,
            ),
            above_target_pose,
        )
        calculated_pose.header.frame_id = "odom"
        return self.move_arm(calculated_pose)
