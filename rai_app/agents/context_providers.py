from rai.agents.langchain.core import (
    ContextProvider,
)

from rai_app.environment import SceneManager


class WarehouseContext(ContextProvider):
    def __init__(self, scene_manager: SceneManager) -> None:
        self.scene_manager = scene_manager

    def get_context(self) -> str:
        """Provide human-readable warehouse context for prompts.

        Returns
        -------
        str
            Description of the warehouse layout, collections, and their
            intended usage, suitable for inclusion in LLM prompts.
        """

        context = (
            "Collection t2 is the outbound shipment table used for preparing shipments."
            "\nCollection t4 is the inspection table used for inspecting returned packages by a human.\n"
            " Tables t1 and t3 have no special purpose, but are available."
        )
        context += self.scene_manager.get_warehouse_collections_description()
        return context
