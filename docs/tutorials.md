# Tutorials

Practical notes for extending the warehouse demo that runs on RobotecAI’s RAI framework. The sections mirror the most frequent customization requests - adding tools, wiring new executors, and updating the simulation scene - and close with a grab bag of extra tips.

## Creating a Warehouse-Aware Tool

Agents interact with the robot through LangChain tools that wrap ROS 2 actions or services. Create a new tool by subclassing `BaseROS2Tool`, pulling in helpers like `SceneManager` or `KairosController`, and returning a short string that Megamind can reason about.

```python
from rai.tools.ros2.base import BaseROS2Tool


class ListOverfilledBins(BaseROS2Tool):
    """Report garbage bins that currently hold trash."""

    name = "list_overfilled_bins"
    description = "Return bins with collected trash based on SceneManager occupancy."

    def _run(self) -> str:
        scene_manager = self.connector.context["scene_manager"]
        bins: list[str] = []
        for tag, collection in scene_manager.slots_collections.items():
            if collection.collection_type == "garbage_bin":
                usage = collection.get_usage_summary()
                if usage["used"] > 0:
                    bins.append(f"{tag}: {usage['used']} items")
        return "No bins require clearing" if not bins else "\n".join(bins)
```

**Hook it up**

- Register the tool in `rai_app/agents/tools.py` (group it with other warehouse helpers).
- Add it to the relevant executor list in `rai_app/agents/agent_orchestrator.py`.
- Optionally expose it to other agents (inspection, safety) if they also need bin status.

## Adding an Executor to Megamind

Executors encapsulate a set of tools plus a tailored prompt so Megamind knows when to delegate. Build the executor, append it to the list before calling `create_megamind(...)`, and mention the new capability in the system prompt template.

```python
from rai.agents.langchain.core import Executor
from rai_app.config.prompts import INVENTORY_AUDIT_PROMPT
from rai_app.agents.tools import ListOverfilledBins
from rai_app.initialization.llms import get_llm_model


def build_inventory_executor(connector, scene_manager):
    llm = get_llm_model("megamind_agent")
    tool = ListOverfilledBins(connector=connector)
    return Executor(
        name="inventory_audit",
        llm=llm,
        tools=[tool],
        system_prompt=INVENTORY_AUDIT_PROMPT,
    )


# In agent_orchestrator.main():
executors = [
    existing_housekeep_executor,
    existing_package_executor,
    existing_image_executor,
    build_inventory_executor(connector, scene_manager),
]
```

Guidance:

- Keep executor prompts concise; highlight when the tools should be used and what output format is expected.
- Update `MEGAMIND_SYSTEM_PROMPT_TEMPLATE` so Megamind advertises the new specialist.
- Run a dry task (`get_initial_megamind_state`) to verify that plan steps route to the new executor.

## Additional Resources

- **Debugging**: `ros2 topic pub --once /user_tasks std_msgs/String "data: 'Audit bins'"` is a quick way to trigger new flows.
- **Configuration**: Copy and tweak the LLM/VLM settings in `config.toml` when switching model endpoints or reasoning modes.
- **Safety & inspection**: Mirror the inspection agent pattern to monitor custom camera feeds or anomaly classes; both follow the same VLM + ROS 2 publish/subscribe blueprint.
