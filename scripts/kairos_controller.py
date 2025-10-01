from abc import ABC, abstractmethod
from typing import Literal, Tuple

from geometry_msgs.msg import Pose
from rai.communication.ros2 import ROS2Connector

from scripts.manipulator_controller import ManipulatorController
from scripts.navigation_controller import NavigationController
from scripts.tools import apply_relative_transform, calculate_relative_transform

LOW_GRASP_Z_THRESHOLD = 0.6
HIGH_GRASP_Z_THRESHOLD = 1.4

NAV_GRIPPING_POSE_DISTANCE = 0.90
NAV_STAGING_POSE_DISTANCE = 1.2
NAV_LOW_GRIPPING_POSE_DISTANCE = 1.2
NAV_LOW_STAGING_POSE_DISTANCE = 2.0
NAV_HIGH_GRIPPING_POSE_DISTANCE = 0.9
NAV_HIGH_STAGING_POSE_DISTANCE = 1.4


class ManipulationStrategy(ABC):
    @abstractmethod
    def get_staging_distance(self) -> float:
        pass

    @abstractmethod
    def get_gripping_distance(self) -> float:
        pass

    @abstractmethod
    def move_arm_to_base_pose(self, mani_ctrl: ManipulatorController):
        pass

    def get_approach_distance(self) -> float:
        return self.get_staging_distance() - self.get_gripping_distance()


class LowManipulationStrategy(ManipulationStrategy):
    def get_staging_distance(self) -> float:
        return NAV_LOW_STAGING_POSE_DISTANCE

    def get_gripping_distance(self) -> float:
        return NAV_LOW_GRIPPING_POSE_DISTANCE

    def move_arm_to_base_pose(self, mani_ctrl: ManipulatorController):
        mani_ctrl.move_arm_to_low_pose()


class HighManipulationStrategy(ManipulationStrategy):
    def get_staging_distance(self) -> float:
        return NAV_HIGH_STAGING_POSE_DISTANCE

    def get_gripping_distance(self) -> float:
        return NAV_HIGH_GRIPPING_POSE_DISTANCE

    def move_arm_to_base_pose(self, mani_ctrl: ManipulatorController):
        mani_ctrl.move_arm_to_high_pose()


class NormalManipulationStrategy(ManipulationStrategy):
    def get_staging_distance(self) -> float:
        return NAV_STAGING_POSE_DISTANCE

    def get_gripping_distance(self) -> float:
        return NAV_GRIPPING_POSE_DISTANCE

    def move_arm_to_base_pose(self, mani_ctrl: ManipulatorController):
        mani_ctrl.move_arm_to_base_pose()


def determine_strategy(pose: Pose, safe_low: bool) -> ManipulationStrategy:
    if safe_low and pose.position.z < LOW_GRASP_Z_THRESHOLD:
        return LowManipulationStrategy()
    elif pose.position.z > HIGH_GRASP_Z_THRESHOLD:
        return HighManipulationStrategy()
    else:
        return NormalManipulationStrategy()


def determine_grasp_type_and_point(
    object_pose: Pose,
    target_slot_pose: Pose,
    top_gripping_point: Pose,
    side_gripping_point: Pose,
) -> Tuple[Literal["top", "side"], Pose]:
    if (
        object_pose.position.z > HIGH_GRASP_Z_THRESHOLD
        or target_slot_pose.position.z > HIGH_GRASP_Z_THRESHOLD
    ):
        return "side", side_gripping_point
    else:
        return "top", top_gripping_point


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
        top_gripping_point: Pose,
        side_gripping_point: Pose,
        safe_low_approach: bool = True,
    ):
        """Move object to target slot.

        Args:
            target_slot_pose (Pose): Target slot pose.
            object_pose (Pose): Object pose.
            top_gripping_point (Pose): Gripping point when grasping from the top.
            side_gripping_point (Pose): Gripping point when grasping from the side.
            safe_low_manipulation (bool): If enabled manipulator will perform special low
            manipulation to avoid collision with objects above.
        """

        grasp_type, gripping_point = determine_grasp_type_and_point(
            object_pose, target_slot_pose, top_gripping_point, side_gripping_point
        )
        self.mani_ctrl.set_grasp_type(grasp_type)

        # Calculate the relative transform from object_pose to gripping_point
        # and apply it to target_slot_pose to get placing_point
        relative_transform = calculate_relative_transform(object_pose, gripping_point)
        placing_point = apply_relative_transform(target_slot_pose, relative_transform)

        self.navigate_to_and_pick(object_pose, gripping_point, safe_low_approach)
        self.navigate_to_and_place(target_slot_pose, placing_point, safe_low_approach)

    def throw_object_to_bin(
        self, bin_slot_pose: Pose, object_pose: Pose, top_gripping_point: Pose
    ):
        self.mani_ctrl.set_grasp_type("top")

        # Calculate the relative transform from object_pose to gripping_point
        # and apply it to target_slot_pose to get placing_point
        relative_transform = calculate_relative_transform(
            object_pose, top_gripping_point
        )
        placing_point = apply_relative_transform(bin_slot_pose, relative_transform)

        self.approach_and_pick(object_pose, top_gripping_point, False)
        self.navigate_to_and_throw_to_bin(bin_slot_pose, placing_point, False)

    def lift_object(self, gripping_point: Pose):
        self.mani_ctrl.move_arm_to_staging_pose(gripping_point)
        self.mani_ctrl.move_arm_to_target_pose(gripping_point)
        self.mani_ctrl.close_gripper()
        self.mani_ctrl.move_arm_to_above_target_pose(gripping_point)

    def place_object(self, placing_point: Pose):
        self.mani_ctrl.move_arm_to_above_target_pose(placing_point)
        self.mani_ctrl.move_arm_to_target_pose(placing_point)
        self.mani_ctrl.open_gripper()
        self.mani_ctrl.move_arm_to_staging_pose(placing_point)

    def navigate_to_and_pick(
        self, object_pose: Pose, gripping_point: Pose, safe_low_approach: bool
    ):
        """Pick an object from the specified pose."""

        strategy = determine_strategy(object_pose, safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            object_pose, strategy.get_staging_distance()
        )
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)

        self.lift_object(gripping_point=gripping_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def approach_and_pick(
        self, object_pose: Pose, gripping_point: Pose, safe_low_approach: bool
    ):
        """Try approaching object from 4 directions and pick it from the specified pose."""

        strategy = determine_strategy(object_pose, safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target(object_pose, strategy.get_staging_distance())
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)

        self.lift_object(gripping_point=gripping_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def navigate_to_and_place(
        self, target_slot_pose: Pose, placing_point: Pose, safe_low_approach: bool
    ):
        """Place an object in the specified pose."""
        strategy = determine_strategy(target_slot_pose, safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            target_slot_pose, strategy.get_staging_distance()
        )
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)

        self.nav_ctrl.move_back(-approach_distance)

        self.place_object(placing_point=placing_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def navigate_to_and_throw_to_bin(
        self, bin_slot_pose: Pose, placing_point: Pose, safe_low_approach: bool
    ):
        """Place an object in the specified pose."""
        strategy = determine_strategy(bin_slot_pose, safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            bin_slot_pose, strategy.get_staging_distance()
        )

        bin_slot_pose.position.y += 0.7
        bin_slot_pose.position.z += 0.4
        self.mani_ctrl.move_arm_to_staging_pose(bin_slot_pose)
        bin_slot_pose.position.y -= 0.7
        bin_slot_pose.position.z -= 0.4

        self.nav_ctrl.move_back(-approach_distance)
        self.place_object(placing_point=placing_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()
