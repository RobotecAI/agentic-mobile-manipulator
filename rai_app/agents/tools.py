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

import base64
import logging
import math
import random
import re
import time
from typing import List, Optional, Tuple, Type, cast

import cv2
import numpy as np
from cv_bridge import CvBridge
from geometry_msgs.msg import Point, Pose, Quaternion
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from rai.messages import HumanMultimodalMessage, MultimodalArtifact
from rai.tools.ros2.base import BaseROS2Tool
from rai.tools.ros2.simple import GetROS2ImageConfiguredTool
from sensor_msgs.msg import Image
from tf_transformations import euler_from_quaternion

from rai_app.agents.vlm_transport import publish_vlm_description
from rai_app.config.vlm_box_condition_prompts import (
    BOX_CONDITION_JSON_SYSTEM_PROMPT,
    BOX_CONDITION_JSON_USER_PROMPT,
    BOX_CONDITION_SYSTEM_PROMPT,
    BOX_CONDITION_TEXT_USER_PROMPT,
    BoxConditionOutput,
)
from rai_app.control.kairos_controller import KairosController, determine_strategy
from rai_app.environment import Collection, SceneManager, Slot, SlotsCollection
from rai_app.geometry_helpers import (
    apply_relative_transform,
    calculate_relative_transform,
    get_global_pose_from_origin,
    get_yaw_difference,
)


class WarehouseTool(BaseROS2Tool):
    kairos_controller: KairosController
    scene_manager: SceneManager

    def refresh_data(self):
        # NOTE (jmatejcz) calling this only before checking collection
        # assumes that packages won't change their positions
        # during tool call
        entities = self.scene_manager.get_entities(name_filter="box")
        if entities:
            self.scene_manager.assign_entities_to_slots(entities)

    def gt_check_if_package_is_present_in_requested_pose(
        self, x: float, y: float, z: float
    ) -> bool:
        """Check if a package is present in the requested pose."""
        entities = self.scene_manager.get_entities(name_filter="cardboard")
        for entity_name, entity_state in entities.items():
            if (
                abs(entity_state.pose.position.x - x) < 0.1
                and abs(entity_state.pose.position.y - y) < 0.1
                and abs(entity_state.pose.position.z - z) < 0.1
            ):
                logging.info(
                    f"[GT] Package {entity_name} is present in the requested pose"
                )
                return True
        return False

    def filter_for_slots_in_arm_range(self, slots: List[Slot]) -> List[Slot]:
        # arm can't access top slots
        # on every rack they are named the same
        excluded_slot_names = [
            "RackSlot10",
            "RackSlot11",
            "RackSlot12",
            "RackSlot22",
            "RackSlot23",
            "RackSlot24",
        ]
        filitered_slots = []
        for slot in slots:
            slot_name_part = slot.tag.split("/")[1]
            if slot_name_part not in excluded_slot_names:
                filitered_slots.append(slot)
        return filitered_slots

    def view_of_racks_poses(self, racks: List[str]) -> Tuple[Pose, Pose]:
        """
        Calculate view poses for one or more racks placed next to each other.

        Args:
            racks: List of rack identifiers (e.g., ["A01"] or ["A01", "A02", "A03"])

        Returns:
            Tuple[Pose, Pose]: Two view poses facing opposite directions

        Raises:
            ValueError: If racks list is empty, racks don't have the same orientation,
                        or have invalid orientation
        """
        if len(racks) == 0:
            raise ValueError("At least 1 rack is required")

        rack_collections = [
            self.scene_manager.slots_collections[rack] for rack in racks
        ]

        if len(racks) == 1:
            return rack_collections[0].middle_poses

        # Multiple racks: get middle_poses for each and validate orientation consistency
        rack_middle_poses = [rack_coll.middle_poses for rack_coll in rack_collections]

        # Use first pose of first rack for orientation reference
        first_qz = rack_middle_poses[0][0].orientation.z
        first_qw = rack_middle_poses[0][0].orientation.w

        # Validate all racks have the same orientation
        for i, (pose1, pose2) in enumerate(rack_middle_poses[1:], start=1):
            rack_qz = pose1.orientation.z
            rack_qw = pose1.orientation.w

            if rack_qz != first_qz or rack_qw != first_qw:
                raise ValueError(
                    f"Rack '{racks[i]}' orientation ({rack_qz}, {rack_qw}) "
                    f"differs from first rack '{racks[0]}' orientation ({first_qz}, {first_qw})"
                )

        # Calculate average position across all racks using middle_poses positions
        total_x = sum(poses[0].position.x for poses in rack_middle_poses)
        total_y = sum(poses[0].position.y for poses in rack_middle_poses)
        total_z = sum(poses[0].position.z for poses in rack_middle_poses)
        count = len(rack_middle_poses)

        avg_position = Point(x=total_x / count, y=total_y / count, z=total_z / count)

        # Get orientation from first rack's middle_poses
        pose1_template, pose2_template = rack_middle_poses[0]

        # Create view poses with averaged position and orientations from middle_poses
        view_pose1 = Pose()
        view_pose1.position = avg_position
        view_pose1.orientation = Quaternion(
            x=pose1_template.orientation.x,
            y=pose1_template.orientation.y,
            z=pose1_template.orientation.z,
            w=pose1_template.orientation.w,
        )

        view_pose2 = Pose()
        view_pose2.position = avg_position
        view_pose2.orientation = Quaternion(
            x=pose2_template.orientation.x,
            y=pose2_template.orientation.y,
            z=pose2_template.orientation.z,
            w=pose2_template.orientation.w,
        )

        return view_pose1, view_pose2

    def approach_and_filter_collection(
        self,
        collection: SlotsCollection,
        slots: List[Slot],
        approach_distance: float = 1.8,
    ) -> List[Slot]:
        """Approaching a collection and filtering slots that are in arms range and in proximity.
        Proximity means that in the row closer to the robot.

        Parameters
        ----------
        collection : SlotsCollection
            The collection to approach.
        slots : List[Slot]
            Initial slots to filter.
        approach_distance : float
            Distance in meters to stop before the collection.

        Returns
        -------
        List[Slot]
            Filtered slots based on proximity and arm range.
        """
        slots_in_range = self.filter_for_slots_in_arm_range(slots)
        filtered_slots = []
        sides_not_available = 0

        for pose in collection.middle_poses:
            try:
                self.kairos_controller.nav_ctrl.approach_target_along_orientation(
                    collection.middle_poses[-1], approach_distance
                )

                if collection.collection_type != "rack":
                    # Approach rack from both viewing poses
                    # when it is not rack, view from 1 side is enough
                    # do not filter slots further
                    filtered_slots = slots_in_range
                    break
                else:
                    # if it is rack go for approach from the other side
                    # and filter slots by proxitimy
                    view_pose = get_global_pose_from_origin(
                        Pose(position=Point(x=approach_distance)), pose
                    )
                    filtered_slots.extend(
                        self._filter_slots_by_proximity(
                            slots=slots_in_range, view_pose=view_pose
                        )
                    )
            except RuntimeError:
                sides_not_available += 1
                continue

            # when both poses not available raise error
            if sides_not_available == 2:
                raise RuntimeError(
                    f"Due to robot's constrution limitations approaching rack {collection.tag} is not possible."
                )

        # Scanning
        time.sleep(1)

        return filtered_slots

    def _filter_slots_by_proximity(
        self, slots: List[Slot], view_pose: Pose
    ) -> List[Slot]:
        """
        Filter slots to only include the closer half based on distance along orientation axis.
        In case of racks there are 2 rows and we want to return only 1st, closer to approach pose.
        In case of table where there is only 1 row return all slots
        """
        if not slots:
            return []

        q = view_pose.orientation
        roll, pitch, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # Forward direction based on yaw
        forward_x = math.cos(yaw)
        forward_y = math.sin(yaw)

        # Calculate signed distance from approach pose to each slot along orientation axis
        slot_distances = {}
        for slot in slots:
            # Vector from approach pose to slot
            dx = abs(slot.origin_pose.position.x - view_pose.position.x)
            dy = abs(slot.origin_pose.position.y - view_pose.position.y)

            # Project onto forward direction (dot product)
            distance_along_orientation = abs(dx * forward_x + dy * forward_y)
            slot_distances[slot.tag] = distance_along_orientation

        # Find the median distance
        sorted_distances = sorted(slot_distances.values())
        median_distance = sorted_distances[(len(sorted_distances) - 1) // 2]

        # Return only slots that are closer than or equal to the median
        filtered_slots = [
            slot for slot in slots if slot_distances[slot.tag] <= median_distance
        ]

        return filtered_slots

    def check_the_origin_collection(
        self,
        collection_name: str,
        item_type: Optional[str] = None,
        approach_distance: float = 1.8,
    ) -> List[Slot]:
        """Retrieve candidate slots containing objects for relocation.

        Parameters
        ----------
        collection_name : str
            Identifier of the source collection (for example ``t5`` or ``K01``).
        item_type : str, optional
            Required item type stored in the package. When provided, only slots
            containing packages with matching metadata are returned.
        approach_distance : float, optional
            Distance in meters to stop the robot before inspecting the
            collection. Defaults to ``2.0``.

        Returns
        -------
        list[Slot]
            Slots that currently contain objects within reachable arm range.

        Raises
        ------
        ValueError
            If the requested collection does not exist in the scene manager.
        RuntimeError
            If no suitable slots are available or no package matches the
            specified ``item_type``.
        """
        self.refresh_data()
        logging.info(
            f"Checking for appropriate objects in origin collection {collection_name}..."
        )
        coll = self.scene_manager.get_collection(tag=collection_name)
        if not coll:
            raise ValueError(f"No collection named {collection_name}")

        used_slots = coll.find_used_slots()
        used_slots = self.approach_and_filter_collection(
            collection=coll, slots=used_slots, approach_distance=approach_distance
        )

        if not used_slots:
            raise RuntimeError(
                f"There is no objects in the collection {collection_name}"
            )

        if item_type:
            slots_with_item = coll.find_slots_with_item_type(item_type=item_type)
            slots_with_item = self.filter_for_slots_in_arm_range(slots_with_item)

            if not slots_with_item:
                raise RuntimeError(
                    f"There is no packages with given item type: {item_type} "
                    f"in the collection {collection_name}"
                )

            slots = list(set(used_slots).intersection(slots_with_item))
            logging.info(
                f"Origin Collection {collection_name} has {len(slots_with_item)} "
                f"appropriate packages with item '{item_type}' in robot's arm range"
            )
            return slots
        else:
            logging.info(
                f"Origin Collection {collection_name} has {len(used_slots)} "
                f"appropriate packages in robot's arm range"
            )
            return used_slots

    def check_the_target_collection(
        self, collection_name: str, approach_distance: float = 1.8
    ) -> List[Slot]:
        """Return empty slots in the target collection.

        Parameters
        ----------
        collection_name : str
            Identifier of the destination collection to inspect.

        Returns
        -------
        list[Slot]
            Empty slots that are reachable by the manipulator.

        Raises
        ------
        ValueError
            If the requested collection does not exist.
        RuntimeError
            If no empty slots are available in the collection.
        """
        self.refresh_data()
        logging.debug(
            f"Checking for empty slots in target collection {collection_name}..."
        )

        coll = self.scene_manager.get_collection(tag=collection_name)
        if not coll:
            raise ValueError(f"No collection named {collection_name}")

        empty_slots = coll.find_empty_slots()
        empty_slots = self.approach_and_filter_collection(
            collection=coll, slots=empty_slots, approach_distance=approach_distance
        )

        if not empty_slots:
            raise RuntimeError(
                f"There is no empty slots in the collection {collection_name}"
            )
        else:
            logging.debug(
                f"Target collection {collection_name} has {len(empty_slots)} empty slots"
            )
            return empty_slots


class NavigateToSloToolInput(BaseModel):
    slot_name: str = Field(..., description="Name of the slot to navigate to")


class NavigateToSlotSyncTool(WarehouseTool):
    name: str = "navigate_to_slot"
    description: str = "Navigate to a specific slot. Use this tool when asked to navigate to specific slot."

    args_schema: Type[NavigateToSloToolInput] = NavigateToSloToolInput

    def _run(self, slot_name: str) -> str:
        """Navigate the mobile base to the pose associated with ``slot_name``."""
        try:
            slot = self.scene_manager.slots[slot_name]
        except KeyError:
            slot_names = self.scene_manager.slots.keys()
            return f"Slot {slot_name} does not exist. Available slot names: {'\n'.join(slot_names)}"

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            target_pose=slot.origin_pose, target_pose_distance=1.0
        )
        return f"Successfully navigated to slot {slot_name}"


class IsPackageDamagedTool(BaseROS2Tool):
    name: str = "is_package_damaged_tool"
    description: str = "Ask VLM if package in current slot is damaged."

    namespace_value: str
    vlm: BaseChatModel

    def _build_ros2_image(self, b64_img: str) -> Image:
        """Decode a base64-encoded RGB image and convert it to a ROS 2 ``Image``."""
        cv2_image = cv2.imdecode(
            np.frombuffer(base64.b64decode(b64_img), np.uint8), cv2.IMREAD_COLOR_RGB
        )
        ros2_image = CvBridge().cv2_to_imgmsg(cv2_image, encoding="passthrough")
        ros2_image.encoding = "rgb8"
        return ros2_image

    def _run(self) -> bool:
        logging.info("Getting image")
        tool = GetROS2ImageConfiguredTool(
            connector=self.connector,
            topic=f"/{self.namespace_value}wrist_camera/camera_image_color",
        )
        _, artifact = tool._run()
        artifact: MultimodalArtifact
        b64_img = artifact["images"][0]

        task = [
            SystemMessage(content=BOX_CONDITION_SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content=BOX_CONDITION_TEXT_USER_PROMPT, images=[b64_img]
            ),
        ]
        descriptive_response = self.vlm.invoke(task)

        structured_task = [
            SystemMessage(content=BOX_CONDITION_JSON_SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content=BOX_CONDITION_TEXT_USER_PROMPT,
                images=[b64_img],
            ),
            AIMessage(content=descriptive_response.content),
            HumanMessage(content=BOX_CONDITION_JSON_USER_PROMPT),
        ]

        descriptive_prompt = ""
        for msg in task:
            descriptive_prompt += msg.pretty_repr() + "\n"

        structured_prompt = ""
        for msg in structured_task:
            structured_prompt += msg.pretty_repr() + "\n"

        vlm = self.vlm.with_structured_output(BoxConditionOutput)
        response = cast(BoxConditionOutput, vlm.invoke(structured_task))
        logging.info(f"Package damaged = {response.box_condition}")
        ros2_image = self._build_ros2_image(b64_img)
        from rai_app.agents.inspection_agent import save_image_to_disk

        images_dir = "./package_condition_images"
        filename = save_image_to_disk(b64_img, images_dir)
        with open(filename + ".descriptive_prompt", "w") as f:
            f.write(descriptive_prompt)
        with open(filename + ".structured_prompt", "w") as f:
            f.write(structured_prompt)
        with open(filename + ".response", "w") as f:
            f.write(response.model_dump_json())
        logging.info(f"Saved image to {filename}")

        publish_vlm_description(
            self.connector,
            ros2_image,
            f"Package condition: {response.box_condition}. \nDescription: {response.box_condition_reason}",
            "Box",
        )
        logging.info("[Box Condition] Published VLM description")

        return True if response.box_condition == "bad" else False


class DescribeImageToolInput(BaseModel):
    prompt: str = Field(..., description="Prompt for the image description model.")


class DescribeImageTool(BaseROS2Tool):
    name: str = "describe_image"
    description: str = "Describe the image in detail."

    args_schema: Type[DescribeImageToolInput] = DescribeImageToolInput

    vlm: BaseChatModel

    def _run(self, prompt: str) -> str:
        SYSTEM_PROMPT = "You are an expert in image analysis and your speciality is the description of images"
        logging.info("Getting image")
        tool = GetROS2ImageConfiguredTool(
            connector=self.connector,
            topic="/wrist_camera/camera_image_color",
        )
        _, artifact = tool._run()
        artifact: MultimodalArtifact
        b64_img = artifact["images"][0]

        task = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content=prompt,
                images=[b64_img],
            ),
        ]
        response = self.vlm.invoke(task)
        logging.info(f"Image described = {response.content}")
        return str(response.content)


class MoveFromCollectionToCollectionInput(BaseModel):
    origin_collection_name: str = Field(
        ..., description="Collection name to move object from"
    )
    item_type: Optional[str] = Field(
        default=None,
        description=(
            "Provide this field if you want to move package with certain type of item inside."
            " If item type is not specified not leave it with default None value."
        ),
    )
    target_collection_name: str = Field(
        ..., description="Collection name to move object to"
    )


class MoveFromCollectionToCollectionTool(WarehouseTool):
    name: str = "move_object_between_collections"
    description: str = (
        "Move ONE object from origin collection to target collection. "
        "A collection might be for example table or rack - like t5 (table) or X02 (rack). "
        "Use this tool when you want to move object from one collection to other. "
        "If you provide item type, the package with certain type of item will be moved."
    )

    args_schema: Type[MoveFromCollectionToCollectionInput] = (
        MoveFromCollectionToCollectionInput
    )

    def _run(
        self,
        origin_collection_name: str,
        target_collection_name: str,
        item_type: Optional[str] = None,
    ):
        """Move one package between collections.

        Parameters
        ----------
        origin_collection_name : str
            Collection containing the source package.
        target_collection_name : str
            Collection expected to receive the package.
        item_type : str, optional
            Specific item type to filter packages before moving.

        Returns
        -------
        str
            Human-readable status describing the performed action or failure
            reason.
        """
        try:
            target_empty_slots = self.check_the_target_collection(
                target_collection_name
            )
            origin_valid_slots = self.check_the_origin_collection(
                origin_collection_name, item_type=item_type
            )
        except Exception as e:
            return str(e)

        if not origin_valid_slots:
            return (
                f"There are no objects in origin collection {origin_collection_name} ."
            )

        origin_slot = origin_valid_slots[0]
        target_slot = target_empty_slots[0]
        origin_object_name = origin_slot.get_obj_name()
        if origin_object_name is None:
            raise ValueError(f"There is no package at origin slot {origin_object_name}")

        target_slot = self.scene_manager.slots[target_slot.tag]
        try:
            logging.info(
                f"Proceeding with moving object from slot {origin_slot.tag} to {target_slot.tag}"
            )
            self.kairos_controller.move_object_to_slot(
                target_slot_name=target_slot.tag,
                entity_name=origin_object_name,
            )
            self.kairos_controller.mani_ctrl.move_arm_to_base_pose()
        except RuntimeError:
            raise RuntimeError(
                f"Due to robot's constrution limitations approaching entity {origin_object_name} is not possible."
            )
        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to move object from {origin_slot.tag} to {target_slot.tag}: {str(e)}"
        finally:
            self.refresh_data()
        return_text = "Successfully moved one "
        return_text += f"package with {str(item_type)}" if item_type else "package"
        return_text += f" from {origin_collection_name} to {target_collection_name}"
        return return_text


class PointInput(BaseModel):
    x: float = Field(..., description="X coordinate of the object location in meters")
    y: float = Field(..., description="Y coordinate of the object location in meters")
    z: float = Field(..., description="Z coordinate of the object location in meters")


class MoveFromPoseToInspectionAreaTool(WarehouseTool):
    name: str = "move_object_from_pose_to_inspection_area"
    description: str = (
        "Move ONE object from a given pose to the inspection area. "
        "Use this tool when you want to move an object from a specific location to the inspection area."
    )

    args_schema: Type[PointInput] = PointInput

    inspection_area_collections: List[str] = ["t4"]

    def _run(
        self,
        x: float,
        y: float,
        z: float,
    ):
        """Move a package from a free-form pose to the inspection area.

        Parameters
        ----------
        x, y, z : float
            Cartesian coordinates of the object pose in meters.


        Returns
        -------
        str
            Human-readable description of the outcome, including the target
            inspection slot or an error message.
        """

        top_gripping_point = Pose(
            position=Point(x=x, y=y, z=z),
        )
        # NOTE setting z to 0.0 will only work when objeect is picked from the ground
        object_pose = Pose(
            position=Point(x=x, y=y, z=0.0),
        )

        all_empty_slots = []
        for collection_name in self.inspection_area_collections:
            empty_slots = self.check_the_target_collection(collection_name)
            all_empty_slots.extend(empty_slots)

        if not all_empty_slots:
            return (
                f"There are no empty slots available in any inspection area collections: "
                f"{', '.join(self.inspection_area_collections)}"
            )

        target_slot = all_empty_slots[0]
        target_slot_pose = target_slot.origin_pose

        try:
            self.kairos_controller.mani_ctrl.set_grasp_type("top")
            self.kairos_controller.disable_safe_low_approach()

            relative_transform = calculate_relative_transform(
                object_pose, top_gripping_point
            )
            placing_point = apply_relative_transform(
                target_slot_pose, relative_transform
            )

            strategy = determine_strategy(
                object_pose, self.kairos_controller.safe_low_approach
            )

            self.kairos_controller.nav_ctrl.approach_target(
                object_pose, strategy.get_staging_distance()
            )

            # TODO(boczekbartek): Use VLM instead of GT
            gt_package_present = self.gt_check_if_package_is_present_in_requested_pose(
                x, y, z
            )

            if not gt_package_present:
                return "Package is no longer present in the requested pose"

            self.kairos_controller.approach_and_pick(object_pose, top_gripping_point)
            self.kairos_controller.navigate_to_and_place(
                target_slot_pose, placing_point
            )
        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return (
                f"Failed to move object from pose ({x}, {y}, {z}) "
                f"to inspection slot {target_slot.tag}: {str(e)}"
            )
        finally:
            self.refresh_data()

        return (
            f"Successfully moved object from pose ({x}, {y}, {z}) "
            f"to inspection area slot {target_slot.tag} in collection "
            f"{target_slot.tag.split('/')[0]}"
        )


class ThrowTrashOutTool(WarehouseTool):
    name: str = "throw_out_trash"
    description: str = "Throw out trash that is at certain location"

    args_schema: Type[PointInput] = PointInput

    def _run(
        self,
        x: float,
        y: float,
        z: float,
    ):
        """Dispose trash identified at the specified pose.

        Parameters
        ----------
        x, y, z : float
            Cartesian coordinates of the trash pose in meters.


        Returns
        -------
        str
            Human-readable status of the disposal action.
        """

        trash_gripping_point = Pose(
            position=Point(x=x, y=y, z=z),
        )
        trash_pose = Pose(
            position=Point(x=x, y=y, z=z / 2),
        )

        # NOTE (jmatejcz) now we have 1 bin, but if we had multiple,
        # we would choose the nearest
        bin_pose = list(
            self.scene_manager.slots_collections["GarbageContainer01"].slots.values()
        )[0].origin_pose
        self.kairos_controller.disable_safe_low_approach()
        strategy = determine_strategy(
            trash_pose, self.kairos_controller.safe_low_approach
        )
        self.kairos_controller.nav_ctrl.approach_target(
            trash_pose, strategy.get_staging_distance()
        )
        if not self.gt_check_if_package_is_present_in_requested_pose(x, y, z):
            logging.info("[GT] Trash is no longer present in the requested pose: ")
            return "Trash is no longer present in the requested pose"

        try:
            self.kairos_controller.throw_object_to_bin(
                bin_slot_pose=bin_pose,
                object_pose=trash_pose,
                top_gripping_point=trash_gripping_point,
            )
            return f"Successfully thrown out trash from {trash_gripping_point.position} to garbage bin"

        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to throw out garbage from {trash_gripping_point.position} to garbage bin: {str(e)}"


class HouseKeepToolInput(BaseModel):
    rack: str = Field(..., description="Rack name to do housekeeping on.")


class HouseKeepTool(WarehouseTool):
    name: str = "do_housekeeping"
    description: str = (
        "Do housekeeping on the given rack. Check for wrongly placed boxes. "
        "You can only provide one rack at a time."
    )
    approach_distance: float = 2.0
    args_schema: Type[HouseKeepToolInput] = HouseKeepToolInput

    def check_collection_boxes_for_misalignment(
        self, collection: SlotsCollection, view_pose: Pose
    ):
        """
        Check collection for misaligned boxes and optionally correct them.
        """
        slots = list(collection.get_all_slots().values())
        closer_slots = self._filter_slots_by_proximity(slots, view_pose)
        closer_slots_within_reach = self.filter_for_slots_in_arm_range(closer_slots)

        for slot in closer_slots_within_reach:
            obj = slot.get_obj_name()
            if obj:
                obj_pose = self.scene_manager.get_pose(entity_name=obj)
                yaw_diff = get_yaw_difference(obj_pose, slot.origin_pose)

                if abs(yaw_diff) > 0.35:
                    self.kairos_controller.allign_object_with_slot(
                        slot_pose=slot.origin_pose, entity_name=obj
                    )
                    # Refresh data after each correction
                    self.refresh_data()

    def check_collection(
        self,
        approach_pose: Pose,
        collection_name: str,
        approach_distance: Optional[float] = None,
    ):
        """Inspect a rack collection for misaligned boxes and optionally correct them."""
        if not approach_distance:
            approach_distance = self.approach_distance

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            approach_pose, approach_distance
        )

        coll = self.scene_manager.slots_collections[collection_name]
        view_pose = get_global_pose_from_origin(
            Pose(position=Point(x=approach_distance)), approach_pose
        )

        self.check_collection_boxes_for_misalignment(coll, view_pose)

    def housekeep(self, rack: str):
        """
        Perform housekeeping on a rack.

        Parameters
        ----------
        rack : str
            Name of the rack to housekeep

        Returns
        -------
        List[str]
            List of status messages for each action taken
        """
        self.refresh_data()

        poses = self.view_of_racks_poses([rack])
        sides_not_available = 0

        for pos in poses:
            try:
                self.check_collection(
                    pos, collection_name=rack, approach_distance=self.approach_distance
                )
            except RuntimeError as e:
                sides_not_available += 1
                logging.warning(e)
            except Exception as e:
                return f"Housekeeping failed: {str(e)}"

        if sides_not_available == 2:
            raise RuntimeError(
                f"Due to robot's construction limitations housekeeping on rack {rack} is not possible."
            )

    def _run(self, rack: str):
        """Execute the housekeeping tool."""
        self.housekeep(rack)
        return f"Housekeep has been completed successfully on rack: {rack}"


class SortReturnedPackageToolInput(BaseModel):
    pass


class SortReturnedPackageTool(WarehouseTool):
    name: str = "sort_returned_package"
    description: str = (
        "Moves returned package to inspection table or designated rack based on item's condition and content. "
        "Run this tool multiple times to move all the packages. "
        "When there are no more packages to sort, the tool will return 'No more packages to sort' message. "
        "This tool does not need parameters. The objects to be sorted are resolved automatically. "
    )
    vlm: BaseChatModel

    args_schema: Type[SortReturnedPackageToolInput] = SortReturnedPackageToolInput

    def _check_if_damaged(self, package_slot: Slot) -> bool:
        self.kairos_controller.mani_ctrl.move_arm_to_base_pose()
        is_box_damaged_tool = IsPackageDamagedTool(
            connector=self.connector,
            vlm=self.vlm,
            namespace_value="",
        )
        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            package_slot.origin_pose, 1.0
        )
        return is_box_damaged_tool._run()

    def _get_free_collections_slot(self, collections_names: List[str]):
        # TODO: Ideally this should be done with item already being held
        for collection_name in collections_names:
            collection = self.scene_manager.get_collection(collection_name)
            if collection is None:
                raise RuntimeError("Internal error. Please notify the operator.")
            free_slots = collection.find_empty_slots()
            free_slots = self.filter_for_slots_in_arm_range(free_slots)
            free_slots = sorted(free_slots, key=lambda x: x.tag)
            if len(free_slots) > 0:
                return free_slots[0]
        raise RuntimeError(
            f"There are no free slots in the collections {collections_names}. Please notify the operator."
        )

    def _get_free_inspection_table_slot(self):
        # TODO: We should first drive to the inspection table in good faith that there are free slots
        # This implementation is hacky

        free_slot = self._get_free_collections_slot([Collection.INSPECTION_TABLE.value])

        return free_slot

    def _extract_item_stored(self, entity_name: str):
        # get what's in the box based on visual cues e.g. qr code
        # this would be usually done using dedicated camera software
        # we are taking the information directly from the object name

        item_name_reqex = re.compile(r"__(.*?)__")
        item_stored = item_name_reqex.search(entity_name)  # type: ignore
        item_stored = cast(str, item_stored.group(1))  # type: ignore
        return item_stored

    def _get_target_collection(self, item_stored: str) -> Slot:
        possible_racks = self.scene_manager.get_object_type_to_racks(item_stored)
        free_slot = self._get_free_collections_slot(possible_racks)
        return free_slot

    def _run(self):
        """Sort a returned package by inspecting damage status and metadata.

        Returns
        -------
        str
            Status message indicating the destination and remaining packages.

        Raises
        ------
        RuntimeError
            If expected packages or slots cannot be retrieved.
        """
        self.connector.logger.info(f"----- Starting {self.__class__.__name__} -----")
        try:
            self.connector.logger.info(
                "Checking for packages in returned packages table"
            )
            used_slots = self.check_the_origin_collection(
                Collection.RETURNED_PACKAGES_TABLE.value, approach_distance=1.5
            )
        except RuntimeError as e:
            if "There is no objects in the collection" in str(e):
                return "No more packages to sort. All packages have been sorted."

        # TODO: random choice to avoid deadlock when a failed tool call is retried
        # should be replaced with a more robust solution

        package_slot = random.choice(used_slots)
        entity_name = package_slot.get_obj_name()
        if not entity_name:
            raise RuntimeError(
                f"There is no object at the slot {package_slot.tag}. This should not happen."
            )

        self.connector.logger.info("Checking if package is damaged")
        is_damaged = self._check_if_damaged(package_slot)
        self.connector.logger.info(f"Is damaged: {is_damaged}")
        if is_damaged is None:
            return "Could not determine the condition of the package, because package is not visible."
        target_slot: Slot | None = None

        if is_damaged:
            target_slot = self._get_free_inspection_table_slot()
            self.connector.logger.info(f"Target slot: {target_slot.tag}")
        else:
            item_stored = self._extract_item_stored(entity_name)
            target_slot = self._get_target_collection(item_stored)
            self.connector.logger.info(f"Target slot: {target_slot.tag}")

        self.connector.logger.info(f"Moving object to slot: {target_slot.tag}")

        self.kairos_controller.move_object_to_slot(
            target_slot_name=target_slot.tag,
            entity_name=entity_name,
        )
        return_text = "Moved "
        return_text += "damaged " if is_damaged else " non-damaged "
        return_text += "package to "
        return_text += "Inspection table " if is_damaged else "respective rack. "
        return_text += f"There are {len(used_slots) - 1} packages left to sort."
        self.connector.logger.info(f"----- Finished {self.__class__.__name__} -----")
        return return_text


class InspectionWarehouseRouteTool(WarehouseTool):
    name: str = "route_around_warehouse"
    description: str = "Performs a route around the warehouse for inspection purpouses"

    def _run(self):
        self.kairos_controller.nav_ctrl.warehouse_route()
        return "Done inspection route around warehouse successfully"
