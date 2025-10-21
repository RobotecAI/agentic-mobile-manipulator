from rai.agents.langchain.core import (
    ContextProvider,
)

from rai_app.environment import Collection, SceneManager


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
            f"Warehouse contains collections like tables or racks. These collection can contain packages.\n"
            f"Table {Collection.OUTBOUND_SHIPMENT_TABLE.value} is the outbound shipment table used for preparing shipments.\n"
            f"Table {Collection.INSPECTION_TABLE.value} is the inspection table used for inspecting returned packages by a human.\n"
            f"Table {Collection.RETURNED_PACKAGES_TABLE.value} is a table where returned packages can be found.\n"
            f"Table {Collection.FREE.value} does not have special purpouse, but is available.\n"
        )
        context += self.scene_manager.get_warehouse_collections_description()
        return context
