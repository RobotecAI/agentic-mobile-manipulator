from rai.agents.langchain.core import (
    ContextProvider,
)

from scripts.scene_manager import SceneManager


class WarehouseContext(ContextProvider):
    def __init__(self, scene_manager: SceneManager) -> None:
        self.scene_manager = scene_manager

    def get_context(self) -> str:
        context = """\nYou are given the names of every collection(table or rack) in the warehouse. Take it as truth, don't confirm it using detection.
Racks are grouped by the items that are stored on them.
If names of collections provided by user are not present, return response to user.
"""
        context += self.scene_manager.get_warehouse_collections_description()
        return context
