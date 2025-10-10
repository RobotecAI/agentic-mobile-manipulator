from abc import ABC, abstractmethod
from typing import Literal, Tuple

import numpy as np
from geometry_msgs.msg import Point, Pose
from rai.communication.ros2 import ROS2Connector

from scripts.manipulator_controller import ManipulatorController
from scripts.navigation_controller import NavigationController
from scripts.scene_manager import SceneManager
from scripts.tools import (
    apply_relative_transform,
    calculate_relative_transform,
    get_global_pose_from_origin,
    get_yaw_difference,
    rotate_pose,
)

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


class KairosController:
    def __init__(self, connector: ROS2Connector, scene_manager: SceneManager) -> None:
        self.connector = connector
        # TODO (jmatejcz) replace it with VisionMock class
        self.scene_manager = scene_manager

        self.node = self.connector.node
        self.logger = self.node.get_logger()

        self.nav_ctrl = NavigationController(self.connector)
        self.mani_ctrl = ManipulatorController(self.connector)

        self.mani_ctrl.move_arm_to_base_pose()
        self.safe_low_approach = True

    def enable_safe_low_approach(self):
        self.safe_low_approach = True

    def disable_safe_low_approach(self):
        self.safe_low_approach = False

    def determine_grasp_type_and_point(
        self,
        object_pose: Pose,
        entity_name: str,
        target_slot_pose: Pose,
    ) -> Tuple[Literal["top", "side"], Pose]:
        if (
            object_pose.position.z > HIGH_GRASP_Z_THRESHOLD
            or target_slot_pose.position.z > HIGH_GRASP_Z_THRESHOLD
        ):
            side_gripping_point = self.scene_manager.find_closest_side_gripping_point(
                entity_name, self.nav_ctrl.get_current_pose()
            )
            return "side", side_gripping_point
        else:
            top_gripping_point = self.scene_manager.get_top_gripping_point(entity_name)
            return "top", top_gripping_point

    def move_object_to_slot(
        self,
        entity_name: str,
        target_slot_name: str,
    ):
        """Move object to target slot.

        Args:
            entity_name (str): name of the object to be moved
            target_slot_name (str): name of the slot where the object should be placed
            scene_manager (SceneManager): instance of SceneManager to get poses
        """
        object_pose = self.scene_manager.find_entity_pose(entity_name)
        target_slot_pose = self.scene_manager.get_slot_pose(target_slot_name)

        grasp_type, gripping_point = self.determine_grasp_type_and_point(
            object_pose, entity_name, target_slot_pose
        )
        self.mani_ctrl.set_grasp_type(grasp_type)

        # Calculate the relative transform from object_pose to gripping_point
        # and apply it to target_slot_pose to get placing_point
        relative_transform = calculate_relative_transform(object_pose, gripping_point)
        placing_point = apply_relative_transform(target_slot_pose, relative_transform)

        self.navigate_to_and_pick(object_pose, gripping_point)
        self.navigate_to_and_place(target_slot_pose, placing_point)

    def allign_object_with_slot(self, slot_pose: Pose, entity_name: str):
        obj_pose = self.scene_manager.get_pose(entity_name=entity_name)
        yaw_diff = get_yaw_difference(obj_pose, slot_pose)
        self.enable_safe_low_approach()
        self.rotate_object(entity_name=entity_name, angle=yaw_diff)

    def rotate_object(
        self,
        entity_name: str,
        angle: float,
    ):
        object_pose = self.scene_manager.find_entity_pose(entity_name=entity_name)
        if object_pose.position.z > HIGH_GRASP_Z_THRESHOLD:
            self.rotate_high_object(entity_name, angle)
            return

        self.mani_ctrl.set_grasp_type("top")
        gripping_point = self.scene_manager.get_top_gripping_point(entity_name)

        strategy = determine_strategy(object_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            object_pose, strategy.get_staging_distance()
        )
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)

        self.lift_object(gripping_point=gripping_point)

        placing_point = rotate_pose(gripping_point, angle, np.array([0, 0, 1]))
        self.place_object(placing_point=placing_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def rotate_high_object(self, entity_name: str, angle: float):
        self.mani_ctrl.set_grasp_type("side")
        initial_slot = self.scene_manager.find_entity_slot(entity_name)
        if initial_slot is None:
            initial_object_pose = self.scene_manager.get_pose(entity_name)
        else:
            initial_object_pose = initial_slot.origin_pose

        initial_object_transform_in_slot = calculate_relative_transform(
            initial_object_pose,
            self.scene_manager.get_pose(entity_name),
        )

        strategy = determine_strategy(initial_object_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()
        self.nav_ctrl.approach_target_along_orientation(
            initial_object_pose, strategy.get_staging_distance()
        )
        # ===== PICK OBJECT FROM HIGH POSITION (SIDE GRASP) =====

        initial_gripping_point = self.scene_manager.find_closest_side_gripping_point(
            entity_name, self.nav_ctrl.get_current_pose()
        )
        object_pose = self.scene_manager.get_pose(entity_name)
        relative_transform = calculate_relative_transform(
            object_pose, initial_gripping_point
        )

        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)
        self.lift_object(gripping_point=initial_gripping_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

        # ===== LOWER OBJECT TO GROUND =====
        self.nav_ctrl.spin(np.pi / 2)
        self.mani_ctrl.move_arm_to_low_pose()

        ground_pose = self.scene_manager.get_pose(entity_name)
        ground_pose.position.z = 0.0
        placing_point = get_global_pose_from_origin(relative_transform, ground_pose)
        self.place_object(placing_point=placing_point, use_staging_pose=False)

        # ===== ROTATE OBJECT ON GROUND (TOP GRASP) =====
        self.nav_ctrl.move_back(0.1)
        old_grasp_type = self.mani_ctrl.grasp_type
        self.mani_ctrl.set_grasp_type("top")
        self.mani_ctrl.move_arm_to_low_pose()
        self.nav_ctrl.move_back(-0.1)

        gripping_point = self.scene_manager.get_top_gripping_point(entity_name)
        placing_point = rotate_pose(gripping_point, angle, np.array([0, 0, 1]))

        self.lift_object(gripping_point=gripping_point)
        self.place_object(placing_point=placing_point)

        # ===== RAISE OBJECT BACK TO HIGH POSITION (SIDE GRASP) =====
        self.nav_ctrl.move_back(0.1)
        self.mani_ctrl.set_grasp_type(old_grasp_type)
        self.mani_ctrl.move_arm_to_low_pose()

        gripping_point = self.scene_manager.find_closest_side_gripping_point(
            entity_name, self.nav_ctrl.get_current_pose()
        )
        object_pose = self.scene_manager.get_pose(entity_name)

        final_object_transform_in_slot = rotate_pose(
            initial_object_transform_in_slot, angle, np.array([0, 0, 1])
        )
        relative_transform = calculate_relative_transform(object_pose, gripping_point)
        final_object_transform = apply_relative_transform(
            initial_object_pose,
            final_object_transform_in_slot,
        )
        placing_point = apply_relative_transform(
            final_object_transform, relative_transform
        )

        self.lift_object(gripping_point=gripping_point)
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)

        self.nav_ctrl.approach_target_along_orientation(
            initial_object_pose, strategy.get_staging_distance()
        )
        self.nav_ctrl.move_back(-approach_distance)
        self.place_object(placing_point=placing_point)
        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

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

        self.disable_safe_low_approach()
        self.approach_and_pick(object_pose, top_gripping_point)
        self.navigate_to_and_throw_to_bin(bin_slot_pose, placing_point)

    def lift_object(self, gripping_point: Pose):
        self.mani_ctrl.move_arm_to_staging_pose(gripping_point)
        self.mani_ctrl.move_arm_to_target_pose(gripping_point)
        self.mani_ctrl.close_gripper()
        self.mani_ctrl.move_arm_to_above_target_pose(gripping_point)

    def place_object(self, placing_point: Pose, use_staging_pose: bool = True):
        if use_staging_pose:
            self.mani_ctrl.move_arm_to_above_target_pose(placing_point)
        self.mani_ctrl.move_arm_to_target_pose(placing_point)
        self.mani_ctrl.open_gripper()
        self.mani_ctrl.move_arm_to_staging_pose(placing_point)

    def navigate_to_and_pick(self, object_pose: Pose, gripping_point: Pose):
        """Pick an object from the specified pose."""

        strategy = determine_strategy(object_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            object_pose, strategy.get_staging_distance()
        )
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)

        self.lift_object(gripping_point=gripping_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def approach_and_pick(self, object_pose: Pose, gripping_point: Pose):
        """Try approaching object from 4 directions and pick it from the specified pose."""

        strategy = determine_strategy(object_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target(object_pose, strategy.get_staging_distance())
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)
        self.nav_ctrl.move_back(-approach_distance)

        self.lift_object(gripping_point=gripping_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def navigate_to_and_place(self, target_slot_pose: Pose, placing_point: Pose):
        """Place an object in the specified pose."""
        strategy = determine_strategy(target_slot_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            target_slot_pose, strategy.get_staging_distance()
        )
        strategy.move_arm_to_base_pose(mani_ctrl=self.mani_ctrl)

        self.nav_ctrl.move_back(-approach_distance)

        self.place_object(placing_point=placing_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def place_on_the_table(self, target_slot_pose: Pose, placing_point: Pose):
        strategy = determine_strategy(target_slot_pose, self.safe_low_approach)
        approach_distance = strategy.get_approach_distance()

        self.nav_ctrl.approach_target_along_orientation(
            target_slot_pose, strategy.get_staging_distance()
        )
        staging_placing_point = apply_relative_transform(
            placing_point, Pose(position=Point(x=0.4 + approach_distance, z=0.1))
        )

        self.mani_ctrl.move_arm_to_staging_pose(staging_placing_point)

        self.nav_ctrl.move_back(-approach_distance)

        self.place_object(placing_point=placing_point)

        self.nav_ctrl.move_back(approach_distance)
        self.mani_ctrl.move_arm_to_base_pose()

    def navigate_to_and_throw_to_bin(self, bin_slot_pose: Pose, placing_point: Pose):
        """Place an object in the specified pose."""
        strategy = determine_strategy(bin_slot_pose, self.safe_low_approach)
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
