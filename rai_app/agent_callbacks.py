import logging
import time
from typing import Any, Dict, List

from langchain_core.callbacks import AsyncCallbackHandler
from rai.communication.ros2 import ROS2Message, ROS2Connector
import logging
from typing import List, Any, Dict


class AgentProgessCallback(AsyncCallbackHandler):
    def __init__(self, connector: ROS2Connector, logger: logging.Logger | None = None):
        self.connector = connector
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.start_time = None
        self.end_time = None

    async def on_llm_end(self, *args, **kwargs):
        self.end_time = time.time()
        if self.start_time is None:
            self.logger.error("LLM start time is not set")
            return
        self.logger.info(
            f"LLM call took {self.end_time - self.start_time:.2f} seconds."
        )

    async def on_chat_model_start(self, *args, **kwargs):
        self.start_time = time.time()

    async def on_chain_end(self, outputs, **kwargs):
        tags = kwargs.get("tags", [])
        # NOTE(jmatejcz) there are 2 types of tags:
        # graph:stepN - they represent a step in the main graph
        # seq:stepN- they repreent a step in the  subgraph
        # we are interested in the main graph as current step or past steps
        # does not change within subgraph ( executors react loop )

        if self.is_main_graph(tags):
            # outputs can be various things depending on what chain is returning
            # but outputs returned by certain nodes
            # will contain the step and steps_done fields
            if isinstance(outputs, dict):
                if "step" in outputs:
                    await self._send_current_step_message(outputs, tags)
                if "steps_done" in outputs:
                    await self._send_past_steps_message(outputs, tags)

    async def _send_current_step_message(
        self, node_state: Dict[str, Any], tags: List[str]
    ):
        task_id = self.get_task_id(tags)
        if "step" in node_state:
            self.connector.send_message(
                message=ROS2Message(
                    payload={
                        "data": f"task-id: {task_id}, current_step: {node_state["step"]}"
                    }
                ),
                msg_type="std_msgs/msg/String",
                target="/agent/current_step",
            )

    async def _send_past_steps_message(
        self, node_state: Dict[str, Any], tags: List[str]
    ):
        task_id = self.get_task_id(tags)
        if "steps_done" in node_state:
            self.connector.send_message(
                message=ROS2Message(
                    payload={
                        "data": f"task-id: {task_id}, current_step: {node_state["steps_done"]}"
                    }
                ),
                msg_type="std_msgs/msg/String",
                target="/agent/past_steps",
            )

    def _extract_subgraph_name(self, tags, node):
        for tag in tags:
            if ":" in tag:
                return tag.split(":")[0]
        return node.split(":")[0] if ":" in node else ""

    def is_main_graph(self, tags: List[str]):
        for tag in tags:
            if "graph:step" in tag:
                return True

    def get_task_id(self, tags: List[str]):
        for tag in tags:
            if "task-id" in tag:
                return tag.split(":")[-1]
