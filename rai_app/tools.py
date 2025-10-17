import base64
import logging
import math
import random
import re
import time
from typing import Dict, List, Optional, Tuple, Type, cast

import cv2
import numpy as np
import pandas as pd
from cv_bridge import CvBridge
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from rai.communication.ros2 import ROS2Message
from rai.messages import HumanMultimodalMessage, MultimodalArtifact, SystemMessage
from rai.tools.ros2.base import BaseROS2Tool
from rai.tools.ros2.simple import GetROS2ImageConfiguredTool
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from tf_transformations import euler_from_quaternion

from rai_app.knowledge import Collection, get_object_type_to_racks
from rai_app.vlm_transport import publish_vlm_description
from scripts.kairos_controller import KairosController
from scripts.scene_manager import SceneManager
from scripts.slots import Slot, SlotsCollection
from scripts.tools import (
    apply_relative_transform,
    calculate_relative_transform,
    get_global_pose_from_origin,
    get_yaw_difference,
)


class WarehouseTool(BaseROS2Tool):
    kairos_controller: KairosController
    scene_manager: SceneManager

    # TODO (jmatejcz) boxes will be distinguishable in the future
    # for now mock it
    # given rack should store a boxes of given type, but does not have to
    # we should check type of boxes we have on the rack/table

    def refresh_data(self):
        # NOTE (jmatejcz) calling this only before checking collection
        # assumes that packages won't change their positions
        # during tool call
        entities = self.scene_manager.get_entities(name_filter="box")
        if entities:
            self.scene_manager.assign_entities_to_slots(entities)

    # TODO (jmatejcz) Filtering by reach could be done on orchestrator side
    # in case we want to include some info about it in raport?
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

    def check_the_origin_collection(
        self,
        collection_name: str,
        item_type: Optional[str] = None,
        approach_distance: float = 2.0,
    ) -> List[Slot]:
        """Check if there is any object to move from given collection.

        Args:
            item_type (Optional[str], optional): When passed, only take into
            consideration packages with certain item type inside. Defaults to None.

        Raises:
            ValueError: raises when there is no such collection
            RuntimeError: raises when there are no objects in slots
            or when there are no packages containing given item type

        Returns:
            List[Slot]: Returns all slots that have objects to move.
            If item type passed, returns only slots where a package that
            has this item type is located.
        """
        self.refresh_data()
        logging.info(
            f"Checking for appropriate objects in origin collection {collection_name}..."
        )
        coll = self.scene_manager.get_collection(tag=collection_name)
        if not coll:
            # return f"No collection named {collection_name}"
            raise ValueError(f"No collection named {collection_name}")

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            coll.middle, approach_distance
        )

        # sleep to mock the visual effect of 'scanning'
        time.sleep(1)
        used_slots = coll.find_used_slots()
        used_slots = self.filter_for_slots_in_arm_range(used_slots)
        if not used_slots:
            raise RuntimeError(
                f"There is no objects in the collection {collection_name}"
            )
        if item_type:
            slots_with_item = coll.find_slots_with_item_type(item_type=item_type)
            slots_with_item = self.filter_for_slots_in_arm_range(slots_with_item)
            if not slots_with_item:
                raise RuntimeError(
                    (
                        f"There is no packages with given item type: {item_type} "
                        f"in the collection {collection_name}"
                    )
                )
            else:
                logging.info(
                    (
                        f"Origin Collection {collection_name} has {len(slots_with_item)} "
                        f"appropriate packages with item '{item_type}' in robot's arm range"
                    )
                )
                return slots_with_item
        else:
            logging.info(
                f"Origin Collection {collection_name} has {len(used_slots)} appropriate packages in robot's arm range"
            )
            return used_slots

    def check_the_target_collection(self, collection_name: str) -> List[Slot]:
        """Check if there are any empty slots in the collection



        Raises:
            ValueError: raises when there is no such collection
            RuntimeError: raises when there are no empty slots in the collection

        Returns:
            List[Slot]: List of empty slots
        """
        self.refresh_data()
        logging.debug(
            f"Checking for empty slots in target collection {collection_name}..."
        )
        coll = self.scene_manager.get_collection(tag=collection_name)
        if not coll:
            raise ValueError(f"No collection named {collection_name}")

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            coll.middle, 2.0
        )

        # sleep to mock the visual effect of 'scanning'
        time.sleep(1)

        empty_slots = coll.find_empty_slots()
        empty_slots = self.filter_for_slots_in_arm_range(empty_slots)
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
        try:
            slot = self.scene_manager.slots[slot_name]
        except KeyError:
            slot_names = self.scene_manager.slots.keys()
            return f"Slot {slot_name} does not exist. Available slot names: {'\n'.join(slot_names)}"

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            target_pose=slot.origin_pose
        )
        return f"Successfully navigated to slot {slot_name}"


class IsPackageDamagedTool(BaseROS2Tool):
    name: str = "is_package_damaged_tool"
    description: str = "Ask VLM if package in current slot is damaged."

    namespace_value: str
    vlm: BaseChatModel

    def _build_ros2_image(self, b64_img: str) -> Image:
        cv2_image = cv2.imdecode(
            np.frombuffer(base64.b64decode(b64_img), np.uint8), cv2.IMREAD_COLOR
        )
        ros2_image = CvBridge().cv2_to_imgmsg(cv2_image, encoding="passthrough")
        ros2_image.encoding = "rgb8"
        return ros2_image

    def _run(self) -> bool:
        SYSTEM_PROMPT = "You are an expert in image analysis and your speciality is the description of images"
        logging.info("Getting image")
        tool = GetROS2ImageConfiguredTool(
            connector=self.connector,
            topic=f"/{self.namespace_value}wrist_camera/camera_image_color",
        )
        _, artifact = tool._run()
        artifact: MultimodalArtifact
        b64_img = artifact["images"][0]

        class ROS2ImgDescription(BaseModel):
            is_package_damaged: bool = Field(
                ..., description="Whether the package is damaged or not"
            )
            description: str = Field(
                ..., description="Short description of the package"
            )

        task = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content="Check if the box is damaged.",
                images=[b64_img],
            ),
        ]
        vlm = self.vlm.with_structured_output(ROS2ImgDescription)
        response = cast(ROS2ImgDescription, vlm.invoke(task))
        logging.info(f"Package damaged = {response.is_package_damaged}")
        ros2_image = self._build_ros2_image(b64_img)
        publish_vlm_description(
            self.connector,
            ros2_image,
            f"Package damaged: {response.is_package_damaged}. \nDescription: {response.description}",
            "Box",
        )
        return response.is_package_damaged


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
            " If not leave it with default value."
        ),
    )
    target_collection_name: str = Field(
        ..., description="Collection name to move object to"
    )


class MoveFromCollectionToCollectionTool(WarehouseTool):
    name: str = "move_object_between_collections"
    description: str = (
        "Move ONE object from origin collection to target colection. "
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
        """Execute complete pick and place operation between slots"""
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
        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to move object from {origin_slot.tag} to {target_slot.tag}: {str(e)}"
        finally:
            self.refresh_data()
        return_text = "Successfully moved one"
        return_text += f"package with {str(item_type)}" if item_type else "package"
        return_text += f" from {origin_collection_name} to {target_collection_name}"
        return return_text


class MoveFromPoseToInspectionAreaToolInput(BaseModel):
    x: float = Field(..., description="X coordinate of the object location in meters")
    y: float = Field(..., description="Y coordinate of the object location in meters")
    z: float = Field(..., description="Z coordinate of the object location in meters")
    qx: float = Field(..., description="X component of orientation quaternion")
    qy: float = Field(..., description="Y component of orientation quaternion")
    qz: float = Field(..., description="Z component of orientation quaternion")
    qw: float = Field(
        ..., description="W component of orientation quaternion (scalar part)"
    )


class MoveFromPoseToInspectionAreaTool(WarehouseTool):
    name: str = "move_object_from_pose_to_inspection_area"
    description: str = (
        "Move ONE object from a given pose to the inspection area. "
        "Use this tool when you want to move an object from a specific location to the inspection area."
    )

    args_schema: Type[MoveFromPoseToInspectionAreaToolInput] = (
        MoveFromPoseToInspectionAreaToolInput
    )

    inspection_area_collections: List[str] = ["t4"]

    def _run(
        self,
        x: float,
        y: float,
        z: float,
        qx: float,
        qy: float,
        qz: float,
        qw: float,
    ):
        """Execute complete pick and place operation from pose to inspection area"""
        top_gripping_point = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=Quaternion(
                x=float(qx),
                y=float(qy),
                z=float(qz),
                w=float(qw),
            ),
        )
        # NOTE setting z to 0.0 will only work when objeect is picked from the ground
        object_pose = Pose(
            position=Point(x=x, y=y, z=0.0),
            orientation=Quaternion(
                x=float(qx),
                y=float(qy),
                z=float(qz),
                w=float(qw),
            ),
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


class ThrowTrashOutInput(BaseModel):
    x: float = Field(..., description="X coordinate of the trash location in meters")
    y: float = Field(..., description="Y coordinate of the trash location in meters")
    z: float = Field(..., description="Z coordinate of the trash location in meters")
    qx: float = Field(..., description="X component of orientation quaternion")
    qy: float = Field(..., description="Y component of orientation quaternion")
    qz: float = Field(..., description="Z component of orientation quaternion")
    qw: float = Field(
        ..., description="W component of orientation quaternion (scalar part)"
    )


class ThrowTrashOutTool(WarehouseTool):
    name: str = "throw_out_trash"
    description: str = "Throw out trash that is at certain location"

    args_schema: Type[ThrowTrashOutInput] = ThrowTrashOutInput

    def _run(
        self,
        x: float,
        y: float,
        z: float,
        qx: float,
        qy: float,
        qz: float,
        qw: float,
    ):
        """Execute throwing out"""

        trash_gripping_point = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=Quaternion(
                x=float(qx),
                y=float(qy),
                z=float(qz),
                w=float(qw),
            ),
        )
        trash_pose = Pose(
            position=Point(x=x, y=y, z=z / 2),
            orientation=Quaternion(
                x=float(qx),
                y=float(qy),
                z=float(qz),
                w=float(qw),
            ),
        )

        # NOTE (jmatejcz) now we have 1 bin, but if we had multiple,
        # we would choose the nearest
        bin_pose = list(
            self.scene_manager.slots_collections["GarbageContainer01"].slots.values()
        )[0].origin_pose
        try:
            self.kairos_controller.throw_object_to_bin(
                bin_slot_pose=bin_pose,
                object_pose=trash_pose,
                top_gripping_point=trash_gripping_point,
            )
            return f"Successfully thrown out trash from {trash_pose} to garbage bin"

        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to throw out garbage from {trash_pose} to garbage bin: {str(e)}"


class HouseKeepTool(WarehouseTool):
    name: str = "do_housekeeping"
    description: str = (
        "drives around warehouse checking for misalligned boxes on the racks"
    )
    task_topic: str
    approach_distance: float = 2.6

    def view_of_racks_pose(self, racks: List[str]) -> Tuple[Pose, Pose]:
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

        first_qz = rack_collections[0].middle.orientation.z
        first_qw = rack_collections[0].middle.orientation.w

        if len(rack_collections) > 1:
            for i, rack_coll in enumerate(rack_collections[1:], start=1):
                rack_qz = rack_coll.middle.orientation.z
                rack_qw = rack_coll.middle.orientation.w

                if rack_qz != first_qz or rack_qw != first_qw:
                    raise ValueError(
                        f"Rack '{racks[i]}' orientation ({rack_qz}, {rack_qw}) "
                        f"differs from first rack '{racks[0]}' orientation ({first_qz}, {first_qw})"
                    )

        # Validate orientation values
        if not (
            (first_qz == 0.0 and first_qw == 1.0)
            or (first_qz == 1.0 and first_qw == 0.0)
            or (first_qz == 0.707)
        ):
            raise ValueError(
                f"Invalid rack orientation: qz={first_qz}, qw={first_qw}. "
                f"Expected (0.0, 1.0), (1.0, 0.0), or (0.707, *)"
            )

        # Calculate average position of all racks
        if len(rack_collections) == 1:
            avg_position = Point(
                x=rack_collections[0].middle.position.x,
                y=rack_collections[0].middle.position.y,
                z=rack_collections[0].middle.position.z,
            )
        else:
            total_x = sum(rack_coll.middle.position.x for rack_coll in rack_collections)
            total_y = sum(rack_coll.middle.position.y for rack_coll in rack_collections)
            total_z = sum(rack_coll.middle.position.z for rack_coll in rack_collections)
            count = len(rack_collections)

            avg_position = Point(
                x=total_x / count, y=total_y / count, z=total_z / count
            )

        view_pose1 = Pose()
        view_pose1.position = avg_position
        view_pose1.orientation = Quaternion(
            x=rack_collections[0].middle.orientation.x,
            y=rack_collections[0].middle.orientation.y,
            z=rack_collections[0].middle.orientation.z,
            w=rack_collections[0].middle.orientation.w,
        )

        # Create second view pose (opposite direction)
        view_pose2 = Pose()
        view_pose2.position = avg_position

        if first_qz == 0.0 and first_qw == 1.0:
            view_pose2.orientation = Quaternion(
                x=rack_collections[0].middle.orientation.x,
                y=rack_collections[0].middle.orientation.y,
                z=1.0,
                w=0.0,
            )
        elif first_qz == 1.0 and first_qw == 0.0:
            view_pose2.orientation = Quaternion(
                x=rack_collections[0].middle.orientation.x,
                y=rack_collections[0].middle.orientation.y,
                z=0.0,
                w=1.0,
            )
        elif first_qz == 0.707:
            view_pose2.orientation = Quaternion(
                x=rack_collections[0].middle.orientation.x,
                y=rack_collections[0].middle.orientation.y,
                z=rack_collections[0].middle.orientation.z,
                w=-rack_collections[0].middle.orientation.w,
            )

        return view_pose1, view_pose2

    def _filter_slots_by_proximity(
        self, slots: Dict[str, Slot], view_pose: Pose
    ) -> Dict[str, Slot]:
        """
        Filter slots to only include the closer half based on distance along orientation axis.
        In case of racks there are 2 rows and we want to return only 1st, closer to approach pose.
        In case of table where there is only 1 row return all slots
        """
        if not slots:
            return {}

        q = view_pose.orientation
        roll, pitch, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # Forward direction based on yaw
        forward_x = math.cos(yaw)
        forward_y = math.sin(yaw)

        # Calculate signed distance from approach pose to each slot along orientation axis
        slot_distances = {}
        for tag, slot in slots.items():
            # Vector from approach pose to slot
            dx = abs(slot.origin_pose.position.x - view_pose.position.x)
            dy = abs(slot.origin_pose.position.y - view_pose.position.y)

            # Project onto forward direction (dot product)
            distance_along_orientation = abs(dx * forward_x + dy * forward_y)
            slot_distances[tag] = distance_along_orientation

        # Find the median distance
        sorted_distances = sorted(slot_distances.values())
        median_distance = sorted_distances[(len(sorted_distances) - 1) // 2]

        # Return only slots that are closer than or equal to the median
        filtered_slots = {
            tag: slot
            for tag, slot in slots.items()
            if slot_distances[tag] <= median_distance
        }

        return filtered_slots

    def check_collection_boxes_for_misallignment(
        self, collection: SlotsCollection, view_pose: Pose
    ):
        slots = collection.get_all_slots()
        closer_slots = self._filter_slots_by_proximity(slots, view_pose)
        closer_slots_within_reach = self.filter_for_slots_in_arm_range(
            list(closer_slots.values())
        )
        for slot in closer_slots_within_reach:
            obj = slot.get_obj_name()
            if obj:
                obj_pose = self.scene_manager.get_pose(entity_name=obj)
                yaw_diff = get_yaw_difference(obj_pose, slot.origin_pose)
                # around 20 degrees
                if abs(yaw_diff) > 0.35:
                    # send new task
                    self.connector.send_message(
                        ROS2Message(
                            payload={
                                "data": f"Rotate box at slot {slot.tag} so that it is aligned with the rack."
                            }
                        ),
                        target=self.task_topic,
                        msg_type="std_msgs/msg/String",
                    )

    def check_collections(
        self,
        approach_pose: Pose,
        collections_names: List[str],
        approach_distance: Optional[float] = None,
    ):
        if not approach_distance:
            approach_distance = self.approach_distance

        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            approach_pose, approach_distance
        )
        for name in collections_names:
            coll = self.scene_manager.slots_collections[name]

            view_pose = get_global_pose_from_origin(
                Pose(position=Point(x=approach_distance)), approach_pose
            )
            self.check_collection_boxes_for_misallignment(coll, view_pose)

    def housekeep_route(self):
        # TODO what about slots that cannot be accessed - top and behind the wall racks
        self.refresh_data()
        df = pd.read_csv("scripts/resources/housekeeping_waypoints.csv")
        waypoints = [
            PoseStamped(
                pose=Pose(
                    position=Point(x=row["x"], y=row["y"], z=row["z"]),
                    orientation=Quaternion(
                        x=row["qx"], y=row["qy"], z=row["qz"], w=row["qw"]
                    ),
                ),
                header=Header(frame_id="odom"),
            )
            for _, row in df.iterrows()
        ]
        Kpos1, Kpos2 = self.view_of_racks_pose(["K01", "K02"])
        Jpos1, Jpos2 = self.view_of_racks_pose(["J01", "J02"])
        Ipos1, Ipos2 = self.view_of_racks_pose(["I01", "I02"])
        Hpos1, Hpos2 = self.view_of_racks_pose(["H01", "H02"])

        L34pos1, L34pos2 = self.view_of_racks_pose(["L03", "L04"])
        L12pos1, L12pos2 = self.view_of_racks_pose(["L01", "L02"])
        L56pos1, L56pos2 = self.view_of_racks_pose(["L05", "L06"])
        L67pos1, L67pos2 = self.view_of_racks_pose(["L06", "L07"])
        L89pos1, L89pos2 = self.view_of_racks_pose(["L08", "L09"])

        G12pos1, G12pos2 = self.view_of_racks_pose(["G01", "G02"])
        G34pos1, G34pos2 = self.view_of_racks_pose(["G03", "G04"])
        G56pos1, G56pos2 = self.view_of_racks_pose(["G05", "G06"])

        A12pos1, A12pos2 = self.view_of_racks_pose(["A01", "A02"])
        A34pos1, A34pos2 = self.view_of_racks_pose(["A03", "A04"])
        A56pos1, A56pos2 = self.view_of_racks_pose(["A05", "A06"])

        F12pos1, F12pos2 = self.view_of_racks_pose(["F01", "F02"])
        F34pos1, F34pos2 = self.view_of_racks_pose(["F03", "F04"])
        F56pos1, F56pos2 = self.view_of_racks_pose(["F05", "F06"])
        F78pos1, F78pos2 = self.view_of_racks_pose(["F07", "F08"])
        F910pos1, F910pos2 = self.view_of_racks_pose(["F09", "F10"])

        B12pos1, B12pos2 = self.view_of_racks_pose(["B01", "B02"])
        B34pos1, B34pos2 = self.view_of_racks_pose(["B03", "B04"])

        C12pos1, C12pos2 = self.view_of_racks_pose(["C01", "C02"])
        C34pos1, C34pos2 = self.view_of_racks_pose(["C03", "C04"])

        D12pos1, D12pos2 = self.view_of_racks_pose(["D01", "D02"])
        D34pos1, D34pos2 = self.view_of_racks_pose(["D03", "D04"])

        self.kairos_controller.nav_ctrl.navigator.navigate_to_pose(pose=waypoints[0])
        self.kairos_controller.mani_ctrl.move_arm_to_rack_view_pose()

        self.check_collections(Kpos1, collections_names=["K01", "K02"])
        self.check_collections(Jpos2, collections_names=["J01", "J02"])
        self.check_collections(Kpos2, collections_names=["K01", "K02"])
        self.check_collections(L12pos1, collections_names=["L01", "L02"])
        self.check_collections(L34pos1, collections_names=["L03", "L04"])

        self.kairos_controller.nav_ctrl.navigator.navigate_to_pose(pose=waypoints[1])

        self.check_collections(L56pos1, collections_names=["L05", "L06"])
        self.check_collections(L67pos1, collections_names=["L06", "L07"])
        self.check_collections(Jpos1, collections_names=["J01", "J02"])
        self.check_collections(Ipos2, collections_names=["I01", "I02"])

        self.kairos_controller.nav_ctrl.navigator.navigate_to_pose(pose=waypoints[2])

        self.check_collections(Ipos1, collections_names=["I01", "I02"])
        self.check_collections(Hpos2, collections_names=["H01", "H02"])
        self.check_collections(L89pos1, collections_names=["L08", "L09"])

        self.kairos_controller.nav_ctrl.navigator.navigate_to_pose(pose=waypoints[3])

        self.check_collections(
            self.scene_manager.slots_collections["L10"].middle,
            collections_names=["L10"],
        )
        self.check_collections(Hpos1, collections_names=["H01", "H02"])
        self.check_collections(G56pos2, collections_names=["G05", "G06"])
        self.check_collections(G34pos2, collections_names=["G03", "G04"])
        self.check_collections(G12pos2, collections_names=["G01", "G02"])

        self.check_collections(A56pos2, collections_names=["A05", "A06"])
        self.check_collections(B34pos1, collections_names=["B03", "B04"])

        self.check_collections(A34pos2, collections_names=["A03", "A04"])
        self.check_collections(B12pos1, collections_names=["B01", "B02"])

        self.check_collections(A12pos2, collections_names=["A01", "A02"])

        self.check_collections(F910pos2, collections_names=["F09", "F10"])
        self.check_collections(F78pos2, collections_names=["F07", "F08"])
        self.check_collections(B12pos2, collections_names=["B01", "B02"])
        self.check_collections(C12pos1, collections_names=["C01", "C02"])
        self.check_collections(B34pos2, collections_names=["B03", "B04"])
        self.check_collections(C34pos1, collections_names=["C03", "C04"])

        self.check_collections(D34pos1, collections_names=["D03", "D04"])
        self.check_collections(C34pos2, collections_names=["C03", "C04"])
        self.check_collections(D12pos1, collections_names=["D01", "D02"])
        self.check_collections(C12pos2, collections_names=["C01", "C02"])
        self.check_collections(F56pos2, collections_names=["F05", "F06"])

        self.check_collections(F34pos2, collections_names=["F03", "F04"])
        # TODO (jmatejcz) add back this rack when the ladder is moved
        # self.check_collections(F12pos2, collections_names=["F01", "F02"])

        self.check_collections(D12pos2, collections_names=["D01", "D02"])

        # Special cases for D03 and D04 where 2.6 distance is to much
        D3_pos = self.scene_manager.slots_collections["D03"].middle
        D3_pos.orientation.y = 1.0
        D3_pos.orientation.w = 0.0
        self.kairos_controller.nav_ctrl.approach_target_along_orientation(D3_pos, 2.0)

        D4_pos = self.scene_manager.slots_collections["D04"].middle
        D4_pos.orientation.y = 1.0
        D4_pos.orientation.w = 0.0
        self.kairos_controller.nav_ctrl.approach_target_along_orientation(D4_pos, 2.0)

    def _run(self):
        self.housekeep_route()
        return "Housekeep route has been completed successfully"


class CorrectBoxPositionToolInput(BaseModel):
    slot_name: str = Field(..., description="Name of the slot at which to rotate box")


class CorrectBoxPositionTool(WarehouseTool):
    name: str = "correct_box_position_in_slot"
    description: str = (
        "Rotate box which is located in given slot to allign it with the slot"
    )

    args_schema: Type[CorrectBoxPositionToolInput] = CorrectBoxPositionToolInput

    def _run(self, slot_name: str):
        slots = self.scene_manager.get_all_slots()
        target_slot = slots[slot_name]
        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            target_pose=target_slot.origin_pose
        )
        obj_name = target_slot.get_obj_name()
        if not obj_name:
            raise RuntimeError(f"There is no object at the slot {target_slot.tag}")

        self.kairos_controller.allign_object_with_slot(
            slot_pose=target_slot.origin_pose, entity_name=obj_name
        )


class SortReturnedPackageToolInput(BaseModel):
    pass


class SortReturnedPackageTool(WarehouseTool):
    name: str = "sort_returned_package"
    description: str = (
        "Moves returned package to inspection table or designated rack based on item's condition and content."
        "Run this tool multiple times to move all the packages."
        "When there are no more packages to sort, the tool will return 'No more packages to sort' message."
        "This tool does not need parameters. The objects to be sorted are resolved automatically."
    )
    vlm: BaseChatModel

    args_schema: Type[SortReturnedPackageToolInput] = SortReturnedPackageToolInput

    def _check_if_damaged(self, package_slot: Slot) -> bool:
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
        # This implementaion is hacky

        free_slot = self._get_free_collections_slot([Collection.INSPECTION_TABLE.value])

        return free_slot

    def _extract_item_stored(self, entity_name: str):
        # get what's in the box based on visual ques e.g. qr code
        # this would be usually done using dedicated camera software
        # we are taking the information directly from the object name

        item_name_reqex = re.compile(r"__(.*?)__")
        item_stored = item_name_reqex.search(entity_name)  # type: ignore
        item_stored = cast(str, item_stored.group(1))  # type: ignore
        return item_stored

    def _get_target_collection(self, item_stored: str) -> Slot:
        possible_racks = get_object_type_to_racks(item_stored)
        free_slot = self._get_free_collections_slot(possible_racks)
        return free_slot

    def _run(self):
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
        return_text += "damaged" if is_damaged else " non-damaged "
        return_text += "package to "
        return_text += "Inspection table" if is_damaged else "respective rack. "
        return_text += f"There are {len(used_slots) - 1} packages left to sort."
        self.connector.logger.info(f"----- Finished {self.__class__.__name__} -----")
        return return_text
