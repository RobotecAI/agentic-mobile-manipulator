import argparse
from typing import Literal, Optional
from rai.communication.ros2 import ROS2Connector, ROS2Context, ROS2Message
from langfuse.decorators import observe
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langfuse.callback import CallbackHandler
import logging
from pprint import pformat
from tools import (
    NavigateToSlotSyncTool,
    MoveFromSlotToSlotTool,
    IsPackageDamagedTool,
)
from scripts.kairos_controller import KairosController
from scripts.scene_manager import SceneManager


from rai.agents.langchain.core import (
    create_megamind,
    Executor,
    get_initial_megamind_state,
    ContextProvider,
)


class SiLParams(BaseModel):
    task: str
    agent_model: str
    agent_vendor: Literal["openai", "ollama"]
    agent_base_url: Optional[str]

    vlm_model: str
    vlm_vendor: Literal["openai", "ollama"]
    vlm_base_url: Optional[str]

    executor_model: str
    executor_vendor: Literal["openai", "ollama"]
    executor_base_url: Optional[str]

    robot_namespace: str
    recurssion_limit: int


langfuse_handler = CallbackHandler()


class WarehouseContext(ContextProvider):

    def __init__(self, scene_manager: SceneManager) -> None:
        self.scene_manager = scene_manager

    def get_context(self) -> str:
        entities = self.scene_manager.get_entities(name_filter="box")
        if entities:
            self.scene_manager.assign_entities_to_slots(entities=entities)
            context = """\n\nYou will be given the layout of the warehouse with collections names and slot names that belong to collections,
like tables or racks. You will also be given if slot is occupied by an object. Take it as truth, don't confirm
it using detection.
"""
            context += "\n"
            context += self.scene_manager.get_warehouse_layout_description()
            context += "\n"
            return context
        else:
            logging.error("Cannot get entities from simulation")
            raise ValueError("Cannot get entities from simulation")


@observe(as_type="generation")
@ROS2Context()
def run_rai_sil(run_params: SiLParams):
    logging.getLogger("rai_agent")
    connector = ROS2Connector()
    scene_manager = SceneManager(
        slots_file="rai_app/scenario_slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    kairos_controller = KairosController(connector=connector)

    vlm_llm = (
        ChatOpenAI(
            model=run_params.vlm_model,
            base_url=run_params.vlm_base_url,
            streaming=True,
        )
        if run_params.agent_vendor == "openai"
        else ChatOllama(
            model=run_params.vlm_model,
            base_url=run_params.vlm_base_url,
            reasoning=False,
        )
    )
    move_from_slot_to_slot_tool = MoveFromSlotToSlotTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    navigation_tool = NavigateToSlotSyncTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    vlm_tool = IsPackageDamagedTool(
        connector=connector,
        namespace_value=run_params.robot_namespace,
        llm=vlm_llm,
    )

    megamind_llm = (
        ChatOpenAI(
            model=run_params.agent_model,
            base_url=run_params.agent_base_url,
            streaming=True,
        )
        if run_params.agent_vendor == "openai"
        else ChatOllama(
            model=run_params.agent_model,
            base_url=run_params.agent_base_url,
            reasoning=False,
        )
    )

    movement_system_prompt = """You are a movement specialist robot agent.
Your role is to handle navigating to slots and moving objects from slot to slot using tools."""

    detection_system_prompt = """You are a detection specialist agent.
Your role is to identify object state using tools."""

    megamind_system_prompt = """You are a mobile robot operating in a warehouse environment for pick-and-place operations.
You manage specialists to whom you will delegate tasks:
- Detection specialist can identify the state of the package at current slot.
- Movement specialist can navigate to slot and move objects from slot to slot.

Use detection agent only when specificly asked about object state, for example if it is damaged. 
Don't place two object in the same spot.
"""
    executor_llm = (
        ChatOpenAI(
            model=run_params.executor_model,
            base_url=run_params.executor_base_url,
            streaming=True,
        )
        if run_params.agent_vendor == "openai"
        else ChatOllama(
            model=run_params.executor_model,
            base_url=run_params.executor_base_url,
            reasoning=False,
        )
    )

    executors = [
        Executor(
            name="movement",
            llm=executor_llm,
            tools=[move_from_slot_to_slot_tool, navigation_tool],
            system_prompt=movement_system_prompt,
        ),
        Executor(
            name="detection",
            llm=executor_llm,
            tools=[vlm_tool],
            system_prompt=detection_system_prompt,
        ),
    ]
    warehouse_context = WarehouseContext(scene_manager=scene_manager)
    agent = create_megamind(
        megamind_system_prompt=megamind_system_prompt,
        megamind_llm=megamind_llm,
        executors=executors,
        context_providers=[warehouse_context],
    )
    initial_state = get_initial_megamind_state(task=run_params.task)

    logging.info(
        f"Starting to run the agent with configuration: {pformat(run_params.model_dump_json())}"
    )


    stop = False
    def emergency_stop_callback(_: ROS2Message):
        """ Sets stop flag to true once called """
        logging.info("Emergency stop callback called")
        nonlocal stop
        stop = True

    connector.register_callback("/emergency_stop", callback=emergency_stop_callback, msg_type="std_msgs/msg/Empty")

    current_step = ""
    steps_done = []

    for subgraph, state in agent.stream(
        initial_state,
        config={
            "recursion_limit": run_params.recurssion_limit,
            "callbacks": [langfuse_handler],
        },
        subgraphs=True,
    ):
        if stop:
            logging.info("Stopping the megamind agent")
            break

        if len(subgraph) == 0:
            subgraph_name = ""
        else:
            subgraph_name = subgraph[0].split(":")[0]
        node = next(iter(state))
        node_state = state[node]

        if "step" in node_state:
            current_step = f'subagent: {subgraph_name}: {node_state["step"]}'

        if "steps_done" in node_state:
            steps_done = f'subagent: {subgraph_name}: {node_state["steps_done"]}'

        logging.info(f"Agent state: {current_step=}\n{steps_done=}")

        connector.send_message(
            message=ROS2Message(payload={"data": current_step}),
            msg_type="std_msgs/msg/String",
            target="/agent/current_step",
        )
        connector.send_message(
            message=ROS2Message(payload={"data": steps_done}),
            msg_type="std_msgs/msg/String",
            target="/agent/past_steps",
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--agent_model", type=str, required=True)
    parser.add_argument(
        "--agent_vendor", type=str, required=True, choices=["openai", "ollama"]
    )
    parser.add_argument("--agent_base_url", type=str, required=False)

    parser.add_argument("--executor_model", type=str, required=False)
    parser.add_argument(
        "--executor_vendor", type=str, required=False, choices=["openai", "ollama"]
    )
    parser.add_argument("--executor_base_url", type=str, required=False)

    parser.add_argument("--vlm_model", type=str, required=False)
    parser.add_argument(
        "--vlm_vendor", type=str, required=False, choices=["openai", "ollama"]
    )
    parser.add_argument("--vlm_base_url", type=str, required=False)

    parser.add_argument("--robot-namespace", type=str, required=True)
    parser.add_argument("--recurssion-limit", type=int, required=False, default=100)

    args, _ = parser.parse_known_args()
    # default to agent model if not passed
    if args.executor_model is None:
        args.executor_model = args.agent_model
    if args.executor_vendor is None:
        args.executor_vendor = args.agent_vendor
    if args.executor_base_url is None:
        args.executor_base_url = args.agent_base_url

    if args.vlm_model is None:
        args.vlm_model = args.agent_model
    if args.vlm_vendor is None:
        args.vlm_vendor = args.agent_vendor
    if args.vlm_base_url is None:
        args.vlm_base_url = args.agent_base_url

    params = SiLParams(**vars(args))
    logging.info(
        f"Starting rai_megamind agent with parameters: {pformat(params.model_dump())}"
    )

    run_rai_sil(params)


if __name__ == "__main__":
    main()
