from geometry_msgs.msg import Pose
from rai.communication.ros2 import ROS2Connector

from scripts.manipulator_controller import ManipulatorController
from scripts.navigation_controller import NavigationController

LOW_GRIPPING_Z_THRESHOLD = 0.6


class KairosController:
    def __init__(
        self,
        connector: ROS2Connector,
    ) -> None:
        self.connector = connector

        self.node = self.connector.node
        self.logger = self.node.get_logger()

        self.nav_ctrl = NavigationController(self.connector)
        self.mani_ctrl = ManipulatorController(self.connector)

        self.mani_ctrl.move_arm_to_base_pose()

    def move_object_to_slot(
        self,
        target_slot_pose: Pose,
        object_pose: Pose,
        object_height: float,
        enable_low_picking: bool = True,
        enable_low_placing: bool = True,
    ):
        """Move object from origin slot to target slot.
        Pick up object from the top using its height

        Args:
            enable_low_picking (bool): If enabled manipulator will perform special low
            picking operation which is needed when picking from a bottom slots of racks
            enable_low_placing (bool): If enabled manipulator will perform special low
            placing operation which is needed when placing to a bottom slots of racks
        """
        self.pick(object_pose, object_height, enable_low_picking)
        self.place(target_slot_pose, object_height, enable_low_placing)

    def move_object_from_gripping_point_to_slot(
        self,
        target_pose: Pose,
        object_pose: Pose,
        object_height: float,
        enable_low_picking: bool = True,
        enable_low_placing: bool = True,
    ):
        """Move object from its gripping to target slot.

        Args:
            enable_low_picking (bool): If enabled manipulator will perform special low
            picking operation which is needed when picking from a bottom slots of racks
            enable_low_placing (bool): If enabled manipulator will perform special low
            placing operation which is needed when placing to a bottom slots of racks
        """
        self.pick(
            object_pose=object_pose,
            object_height=0.0,
            low_picking=enable_low_picking,
        )
        self.place(target_pose, object_height, low_placing=enable_low_placing)

    def pick(self, object_pose: Pose, object_height: float, low_picking: bool):
        if low_picking and object_pose.position.z < LOW_GRIPPING_Z_THRESHOLD:
            self.pick_low(object_pose, object_height)
            return

        self.nav_ctrl.navigate_to_staging_pose(object_pose)
        self.nav_ctrl.move_back(-0.2)

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(object_pose, object_height)

        self.mani_ctrl.close_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)

        self.nav_ctrl.move_back()

        self.mani_ctrl.move_arm_to_base_pose()

    def pick_low(self, object_pose: Pose, object_height: float):
        self.nav_ctrl.navigate_to_low_staging_pose(object_pose)
        self.mani_ctrl.move_arm_to_low_base_pose()
        self.nav_ctrl.move_back(-0.8)

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(object_pose, object_height)

        self.mani_ctrl.close_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(object_pose, object_height)

        self.nav_ctrl.move_back(0.8)

        self.mani_ctrl.move_arm_to_base_pose()

    def place(self, target_pose: Pose, object_height: float, low_placing: bool):
        if low_placing and target_pose.position.z < LOW_GRIPPING_Z_THRESHOLD:
            self.place_low(target_pose, object_height)
            return
        self.nav_ctrl.navigate_to_staging_pose(target_pose)
        self.nav_ctrl.navigate_to_gripping_pose(target_pose)

        self.mani_ctrl.move_arm_to_staging_pose(target_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(target_pose, object_height)

        self.mani_ctrl.open_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(target_pose, object_height)
        self.mani_ctrl.move_arm_to_base_pose()

        self.nav_ctrl.move_back()

    def place_low(self, slot_pose: Pose, object_height: float):
        self.nav_ctrl.navigate_to_low_staging_pose(slot_pose)
        self.mani_ctrl.move_arm_to_low_base_pose()
        self.nav_ctrl.move_back(-0.8)

        self.mani_ctrl.move_arm_to_staging_pose(slot_pose, object_height)
        self.mani_ctrl.move_arm_to_gripping_pose(slot_pose, object_height)

        self.mani_ctrl.open_gripper()

        self.mani_ctrl.move_arm_to_staging_pose(slot_pose, object_height)

        self.nav_ctrl.move_back(0.8)

        self.mani_ctrl.move_arm_to_base_pose()
