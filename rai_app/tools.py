import logging
import time
from typing import List, Optional, Type, cast

from geometry_msgs.msg import Point, Pose, Quaternion
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from rai.messages import HumanMultimodalMessage, MultimodalArtifact, SystemMessage
from rai.tools.ros2.base import BaseROS2Tool
from rai.tools.ros2.simple import GetROS2ImageConfiguredTool

from scripts.kairos_controller import KairosController
from scripts.scene_manager import SceneManager
from scripts.slots import Slot


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
        self, collection_name: str, item_type: Optional[str] = None
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

        # navigate to the middle , in front/back of the collection
        # TODO (jmatejcz) check from other side if this unavialble after merging of navigation update

        # TODO (jamtejcz) should rack be always checked from both sides?
        self.kairos_controller.nav_ctrl.approach_target_along_orientation(
            coll.middle, 2.0
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
        logging.info(
            f"Checking for empty slots in target collection {collection_name}..."
        )
        coll = self.scene_manager.get_collection(tag=collection_name)
        if not coll:
            raise ValueError(f"No collection named {collection_name}")

        # navigate to the middle , in front/back of the collection
        # TODO (jmatejcz) check from other side if this unavialble after merging of navigation update

        # TODO (jamtejcz) should rack be always checked from both sides?
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
            logging.info(
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
    llm: BaseChatModel

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

        task = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content="Check if the box is damaged.",
                images=[b64_img],
            ),
        ]
        llm = self.llm.with_structured_output(ROS2ImgDescription)
        response = cast(ROS2ImgDescription, llm.invoke(task))
        logging.info(f"Package damaged = {response.is_package_damaged}")
        return response.is_package_damaged


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

        origin_object_pose = self.scene_manager.get_pose(entity_name=origin_object_name)

        target_slot = self.scene_manager.slots[target_slot.tag]
        gripping_point = self.scene_manager.get_gripping_point(origin_object_name)
        side_gripping_point = self.scene_manager.get_pose(
            origin_object_name + "_SideGrippingPoint"
        )
        try:
            logging.info(
                f"Proceeding with moving object from slot {origin_slot.tag} to {target_slot.tag}"
            )
            self.kairos_controller.move_object_to_slot(
                target_slot_pose=target_slot.origin_pose,
                object_pose=origin_object_pose,
                top_gripping_point=gripping_point,
                side_gripping_point=side_gripping_point,
            )
        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to move object from {origin_slot.tag} to {target_slot.tag}: {str(e)}"
        finally:
            entities = self.scene_manager.get_entities(name_filter="box")
            if entities:
                self.scene_manager.assign_entities_to_slots(entities=entities)
        return f"Successfully moved ONE object from {origin_collection_name} to {target_collection_name}"


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
