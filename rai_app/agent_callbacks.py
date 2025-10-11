import logging
import time
from typing import Any, Dict, List

from langchain_core.callbacks import AsyncCallbackHandler
from rai.communication.ros2 import ROS2Connector, ROS2HRIMessage, ROS2Message


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
                if "steps_done" in outputs:
                    await self._send_past_steps_message(outputs)

    async def _send_past_steps_message(self, node_state: Dict[str, Any]):
        if "steps_done" in node_state:
            msg = ""
            for step in node_state["steps_done"]:
                msg += step
                msg += "\n"
            self.connector.send_message(
                message=ROS2Message(payload={"data": msg}),
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


class AgentActionsCallback:
    def __init__(self, connector: ROS2Connector, topic: str) -> None:
        self.connector = connector
        self.action_topic = topic

    async def _send_text(self, task_id: str, node_name: str, text: str, topic: str):
        msg = ROS2HRIMessage(
            payload={"text": text, "communication_id": f"{node_name}:{task_id}"}
        )
        self.connector.send_message(
            message=msg,
            msg_type="rai_interfaces/msg/HRIMessage",
            target=topic,
        )

    async def _send_tool_call(
        self,
        task_id: str,
        node_name: str,
        tool_name: str,
        tool_call_args: Dict[str, str],
        topic: str,
    ):
        payload = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_args": tool_call_args,
        }
        msg = ROS2HRIMessage(
            payload={"text": str(payload), "communication_id": f"{node_name}:{task_id}"}
        )
        self.connector.send_message(
            message=msg,
            msg_type="rai_interfaces/msg/HRIMessage",
            target=topic,
        )

    async def process_stream_chunk(self, chunk):
        """Process streaming messages (both text tokens and tool calls)."""

        subgraph_tuple, mode, data = chunk

        # extract node name from subgraph (e.g. 'movement')
        subgraph = subgraph_tuple[0]
        node_name, node_run_id = subgraph.split(":")

        # NOTE skipping analyzer node as its output is already in past_steps
        if node_name == "structured_output":
            return
        if mode != "messages":
            return

        message_chunk, metadata = data

        if hasattr(message_chunk, "additional_kwargs"):
            reasoning = message_chunk.additional_kwargs.get("reasoning_content")
            if reasoning:
                await self._send_text(
                    task_id=node_run_id,
                    text=reasoning,
                    topic=self.action_topic,
                    node_name=node_name,
                )

        if hasattr(message_chunk, "content") and message_chunk.content:
            await self._send_text(
                task_id=node_run_id,
                text=message_chunk.content,
                topic=self.action_topic,
                node_name=node_name,
            )

        if hasattr(message_chunk, "tool_calls") and message_chunk.tool_calls:
            for tool_call in message_chunk.tool_calls:
                await self._send_tool_call(
                    task_id=node_run_id,
                    tool_call_args=tool_call["args"],
                    tool_name=tool_call["name"],
                    topic=self.action_topic,
                    node_name=node_name,
                )
