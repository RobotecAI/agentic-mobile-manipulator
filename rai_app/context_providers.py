from rai.agents.langchain.core import (
    ContextProvider,
)

from scripts.scene_manager import SceneManager


class WarehouseContext(ContextProvider):
    def __init__(self, scene_manager: SceneManager) -> None:
        self.scene_manager = scene_manager

    def get_context(self) -> str:
        context = (
            "Collection t2 is the outbound shipment table used for preparing shipments."
            "\nCollection t4 is the inspection table used for inspecting returned packages by a human.\n"
            " Tables t1 and t3 have no special purpose, but are available."
        )
        context += self.scene_manager.get_warehouse_collections_description()
        return context
