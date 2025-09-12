from geometry_msgs.msg import Pose
from manipulator_controller import ManipulatorController
from navigation_controller import NavigationController
from rai.communication.ros2 import ROS2Connector


class KairosController:
    def __init__(
        self,
        connector: ROS2Connector,
        namespace: str = "",
        ros_package_name: str = "robotec_kairos_ur10",
    ) -> None:
        self.connector = connector
        self.namespace = namespace
        self.ros2_package_name = ros_package_name

        self.node = self.connector.node
        self.logger = self.node.get_logger()

        self.nav_ctrl = NavigationController()
        self.mani_ctrl = ManipulatorController(
            self.connector, self.namespace, self.ros2_package_name
        )

        self.mani_ctrl.move_arm_to_base_pose()

    def place_object_on_rack(self, slot_pose, object_pose, object_height):
        self.pick(object_pose, object_height)
        self.place(slot_pose, object_height)

    def pick(self, object_pose: Pose, object_height: float):
        self.nav_ctrl.navigate_to_staging_pose(object_pose)
        self.nav_ctrl.navigate_to_gripping_pose(object_pose)

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(object_pose, object_height)

        self.mani_ctrl.close_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)

        self.nav_ctrl.move_back()

        self.mani_ctrl.move_arm_to_base_pose()

    def place(self, slot_pose: Pose, object_height: float):
        self.nav_ctrl.navigate_to_staging_pose(slot_pose)
        self.nav_ctrl.navigate_to_gripping_pose(slot_pose)

        self.mani_ctrl.move_arm_to_staging_pose(slot_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(slot_pose, object_height)

        self.mani_ctrl.open_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(slot_pose, object_height)
        self.mani_ctrl.move_arm_to_base_pose()

        self.nav_ctrl.move_back()
