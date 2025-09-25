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
    description: str = (
        "Navigate to a specific slot. Use this tool when asked to navigate to specific slot."
    )

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
            self.kairos_controller.move_object_to_slot(
                target_slot_pose=target_slot.origin_pose,
                object_pose=origin_object_pose,
                object_height=object_height,
            )
            return f"Successfully moved object from {origin_slot_name} to {target_slot_name}"

        except Exception as e:
            logging.error(f"Error during move operation: {str(e)}")
            return f"Failed to move object from {origin_slot_name} to {target_slot_name}: {str(e)}"


class MoveFromCollectionToCollectionInput(BaseModel):
    origin_collection_name: str = Field(
        ..., description="Collection name to move objects from"
    )
    target_collection_name: str = Field(
        ..., description="Collection name to move objects to"
    )


class MoveFromCollectionToCollectionTool(WarehosueTool):
    name: str = "move_objects_between_collections"
    description: str = (
        "Move ALL objects from origin collection to target colection."
        " A collection might be for example table or rack - like t5 (table) or X02 (rack)"
        "Use this tool when asked to move objects from one collection to other"
    )

    args_schema: Type[MoveFromCollectionToCollectionInput] = (
        MoveFromCollectionToCollectionInput
    )

    def _run(self, origin_collection_name: str, target_collection_name: str):
        """Execute complete pick and place operation between slots"""

        try:
            origin_collection = self.scene_manager.slots_collections[
                origin_collection_name
            ]
        except KeyError:
            collection_names = self.scene_manager.slots_collections.keys()
            raise KeyError(
                f"Collection {origin_collection_name} does not exist. Available collection names: {"\n".join(collection_names)}"
            )

        try:
            target_collection = self.scene_manager.slots_collections[
                target_collection_name
            ]
        except KeyError:
            collection_names = self.scene_manager.slots_collections.keys()
            return f"Collection {target_collection_name} does not exist. Available collection names: {"\n".join(collection_names)}"

        origin_used_slot_names = origin_collection.find_used_slots()
        if not origin_used_slot_names:
            return f"There are no objects in {origin_collection_name} collection"

        target_empty_slot_names = target_collection.find_empty_slots()
        ## TODO (jmatejcz) only this slot does work in current sim
        filtered_target_names = []
        for name in target_empty_slot_names:
            if (
                "rackslot5" in name.lower()
                or "rackslot4" in name.lower()
                or "rackslot6" in name.lower()
            ):
                filtered_target_names.append(name)
        if len(origin_used_slot_names) > len(target_empty_slot_names):
            return (
                f"{target_collection.collection_type} {target_collection_name} has only {len(target_empty_slot_names)} "
                f"empty slots and {origin_collection.collection_type} {origin_collection_name} has {len(origin_used_slot_names)} objects to move"
            )

        for origin_slot_name, target_slot_name in zip(
            origin_used_slot_names, filtered_target_names
        ):
            try:
                origin_object_name = self.scene_manager.slots[
                    origin_slot_name
                ].get_obj_name()
                origin_object_pose = self.scene_manager.get_pose(
                    entity_name=origin_object_name
                )
                object_height = self.scene_manager.get_object_height(
                    object_name=origin_object_name
                )
                target_slot = self.scene_manager.slots[target_slot_name]
                self.kairos_controller.move_object_to_slot(
                    target_slot_pose=target_slot.origin_pose,
                    object_pose=origin_object_pose,
                    object_height=object_height,
                )
            except Exception as e:
                logging.error(f"Error during move operation: {str(e)}")
                return f"Failed to move object from {origin_slot_name} to {target_slot_name}: {str(e)}"

        return f"Successfully moved objects from {origin_collection_name} to {target_collection_name}"
