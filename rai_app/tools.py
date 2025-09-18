from typing import Type, cast

from pydantic import BaseModel, Field

from rai.tools.ros2.base import BaseROS2Tool
import logging
from rai.tools.ros2.simple import GetROS2ImageConfiguredTool


from scripts.kairos_controller import KairosController
from scripts.scene_manager import SceneManager
from langchain_core.language_models.chat_models import BaseChatModel

from rai.messages import HumanMultimodalMessage, MultimodalArtifact, SystemMessage


class WarehosueTool(BaseROS2Tool):
    kairos_controller: KairosController
    scene_manager: SceneManager


class NavigateToSlotoolInput(BaseModel):
    slot_name: str = Field(..., description="Name of the slot to navigate to")


class NavigateToSlotSyncTool(WarehosueTool):
    name: str = "navigate_to_slot"
    description: str = "Navigate to a specific slot"

    args_schema: Type[NavigateToSlotoolInput] = NavigateToSlotoolInput

    def _run(self, slot_name: str) -> str:
        try:
            slot = self.scene_manager.slots[slot_name]
        except KeyError:
            slot_names = self.scene_manager.slots.keys()
            return f"Slot {slot_name} does not exist. Available slot names: {"\n".join(slot_names)}"

        self.kairos_controller.nav_ctrl.navigate_to_staging_pose(
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


class MoveFromSlotToSlotToolInput(BaseModel):
    origin_slot_name: str = Field(..., description="Slot name to move object from")
    target_slot_name: str = Field(..., description="Slot name to move object to")


class MoveFromSlotToSlotTool(WarehosueTool):
    name: str = "move_object_from_slot_to_another_slot"
    description: str = (
        "Move object from origin slot than navigate to target slot and drop it there"
    )

    args_schema: Type[MoveFromSlotToSlotToolInput] = MoveFromSlotToSlotToolInput

    def _run(self, origin_slot_name: str, target_slot_name: str):
        """Execute complete pick and place operation between slots"""
        try:
            origin_slot = self.scene_manager.slots[origin_slot_name]
        except KeyError:
            slot_names = self.scene_manager.slots.keys()
            return f"Slot {origin_slot_name} does not exist. Available slot names: {"\n".join(slot_names)}"

        try:
            target_slot = self.scene_manager.slots[target_slot_name]
        except KeyError:
            slot_names = self.scene_manager.slots.keys()
            return f"Slot {target_slot_name} does not exist. Available slot names: {"\n".join(slot_names)}"

        origin_object_name = origin_slot.get_obj_name()
        target_object_name = target_slot.get_obj_name()

        if origin_object_name is None:
            raise ValueError(f"There is no package at origin slot {origin_object_name}")
        if target_object_name:
            raise ValueError(
                f"There is already a package at target slot {target_object_name}"
            )

        try:
            # Get origin slot and object information
            origin_object_pose = self.scene_manager.get_pose(
                entity_name=origin_object_name
            )
            object_height = self.scene_manager.get_object_height(
                object_name=origin_object_name
            )
            target_slot = self.scene_manager.slots[target_slot_name]
            ############### Navigate to origin slot and pick up from origin slot
            self.kairos_controller.pick(
                object_pose=origin_object_pose, object_height=object_height
            )

            ##################### Navigate to target slot and drop at target
            self.kairos_controller.place(
                target_slot.origin_pose, object_height=object_height
            )
            return f"Successfully moved object from {origin_slot_name} to {target_slot_name}"

        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to move object from {origin_slot_name} to {target_slot_name}: {str(e)}"
