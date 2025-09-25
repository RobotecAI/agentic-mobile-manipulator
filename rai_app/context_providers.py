import logging
from scripts.scene_manager import SceneManager


from rai.agents.langchain.core import (
    ContextProvider,
)


class WarehouseContext(ContextProvider):

    def __init__(self, scene_manager: SceneManager) -> None:
        self.scene_manager = scene_manager

    def get_context(self) -> str:
        entities = self.scene_manager.get_entities(name_filter="box")
        if entities:
            self.scene_manager.assign_entities_to_slots(entities=entities)
            context = """\n\nYou are given the names of every collection(table or rack) in the warehouse. Take it as truth, don't confirm it using detection.
If names of collections provided by user are not present, return response to user.
"""
            context += "\n"
            context += self.scene_manager.get_warehouse_collections_description()
            context += "\n"
            return context
        else:
            logging.error("Cannot get entities from simulation")
            # TODO (jmatejcz) catch this error
            raise ValueError("Cannot get entities from simulation")
