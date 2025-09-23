from typing import Dict

from geometry_msgs.msg import Pose, PoseStamped
from rai.communication.ros2 import ROS2Connector, ROS2Message


class ManipulatorController:
    """Passthrough class for the MoveIt2 agent"""

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
        self,
        connector: ROS2Connector | None = None,
    ):
        self.connector = connector or ROS2Connector(executor_type="single_threaded")

    def open_gripper(self):
        response = self.connector.service_call(
            message=ROS2Message(payload={"gripper_state": 1}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
        return response

    def close_gripper(self):
        response = self.connector.service_call(
            message=ROS2Message(payload={"gripper_state": 2}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
        return response

    def move_arm(self, pose: PoseStamped):
        response = self.connector.service_call(
            message=ROS2Message(payload={"target_pose": pose}),
            target="/rai/moveit2/move_arm",
            msg_type="rai_interfaces/srv/MoveArm",
        )
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
        return response

    def move_arm_to_base_pose(self):
        return self.set_arm_joints(self.BASE_JOINT_VALUES)

    def move_arm_to_low_base_pose(self):
        return self.set_arm_joints(self.LOW_BASE_JOINT_VALUES)

    def move_arm_to_staging_pose(self, target_pose: Pose, object_height: float):
        calculated_pose = PoseStamped()
        calculated_pose.pose.position.x = target_pose.position.x
        calculated_pose.pose.position.y = target_pose.position.y
        calculated_pose.pose.position.z = (
            target_pose.position.z + object_height + self.ARM_STAGING_POSE_DISTANCE
        )
        calculated_pose.header.frame_id = "odom"
        return self.move_arm(calculated_pose)

    def move_arm_to_gripping_pose(self, target_pose: Pose, object_height: float):
        calculated_pose = PoseStamped()
        calculated_pose.pose.position.x = target_pose.position.x
        calculated_pose.pose.position.y = target_pose.position.y
        calculated_pose.pose.position.z = target_pose.position.z + object_height
        calculated_pose.header.frame_id = "odom"
        return self.move_arm(calculated_pose)
