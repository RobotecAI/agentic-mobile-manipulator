# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Developed by Robotec.ai sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from rai.communication.ros2 import ROS2Connector, ROS2HRIMessage, ROS2Message


class AgentProgressCallback(AsyncCallbackHandler):
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
            self.connector.send_message(
                message=ROS2Message(payload={"data": node_state["steps_done"]}),
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
            payload={
                "text": json.dumps(payload),
                "communication_id": f"{node_name}:{task_id}",
            }
        )
        self.connector.send_message(
            message=msg,
            msg_type="rai_interfaces/msg/HRIMessage",
            target=topic,
        )

    async def process_stream_chunk(self, chunk):
        """Handle streaming messages emitted by LangChain subgraphs.

        Parameters
        ----------
        chunk : tuple
            Tuple emitted by ``agent.astream`` containing subgraph metadata,
            message mode, and message payload. Expected structure:
            ``((subgraph, node_run_id), mode, data)``.

        Returns
        -------
        None
            The method forwards messages through ROS 2 topics and does not
            return a value.
        """

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


class OrchestratorTasksNotifier:
    def __init__(
        self,
        connector: ROS2Connector,
        current_task_topic: str,
        tasks_queue_topic: str,
        heartbeat_topic: str,
    ) -> None:
        self.connector = connector
        self.current_task_topic = current_task_topic
        self.tasks_queue_topic = tasks_queue_topic
        self.heartbeat_topic = heartbeat_topic

    def send_main_task(self, task: str):
        self.connector.send_message(
            message=ROS2Message(payload={"data": task}),
            msg_type="std_msgs/msg/String",
            target=self.current_task_topic,
        )

    def send_tasks_queue(self, tasks: List[str]):
        msg = "|".join(tasks)
        self.connector.send_message(
            message=ROS2Message(payload={"data": msg}),
            msg_type="std_msgs/msg/String",
            target=self.tasks_queue_topic,
        )

    def send_heartbeat(self):
        self.connector.send_message(
            message=ROS2Message(payload={}),
            msg_type="std_msgs/msg/Header",
            target=self.heartbeat_topic,
        )


def _stringify_content(content: Any) -> str:
    """Flatten a message's content to text. Multimodal blocks (VLM image parts)
    are summarized as ``[image]`` so the log stays readable and small."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype in ("image_url", "image"):
                    parts.append("[image]")
                else:
                    parts.append(f"[{btype or 'block'}]")
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    return str(content)


def _guard(fn):
    """Never let a tracing error break the agent run."""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - tracing must not crash the agent
            self.logger.warning(f"trace callback {fn.__name__} failed: {exc}")

    return wrapper


class ConversationFileCallback(BaseCallbackHandler):
    """Dump the full LLM conversation (orchestrator + subagents) to a run directory.

    Register it in the orchestrator's ``langchain_callbacks`` list. That list is
    passed to ``astream(config={"callbacks": ...}, subgraphs=True)``, and LangGraph
    propagates config callbacks into every subgraph, so both the megamind
    orchestrator and its executor subagents are captured in one place.

    Writes two files per run:
      - ``log.txt``   human-readable transcript (messages, tool calls, results)
      - ``trace.jsonl`` one JSON record per event (machine-readable)

    Enabled by default to ``runs/<timestamp>/``. Override the directory with
    ``AMM_TRACE_DIR``; disable entirely with ``AMM_TRACE=0``.
    """

    # Run inline on the event loop so concurrent subgraph events don't interleave
    # partial lines in the files.
    run_inline = True

    def __init__(self, out_dir: str | Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.text_path = self.out_dir / "log.txt"
        self.jsonl_path = self.out_dir / "trace.jsonl"
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Conversation trace -> {self.out_dir}")

    @classmethod
    def from_env(cls) -> Optional["ConversationFileCallback"]:
        """Build from env, or return None if disabled (``AMM_TRACE=0``)."""
        if os.getenv("AMM_TRACE", "1") == "0":
            return None
        out_dir = os.getenv("AMM_TRACE_DIR") or os.path.join(
            "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        )
        return cls(out_dir)

    # ── writers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _write_text(self, block: str) -> None:
        with open(self.text_path, "a", encoding="utf-8") as f:
            f.write(block.rstrip() + "\n")

    def _write_json(self, record: Dict[str, Any]) -> None:
        record = {"ts": datetime.now().isoformat(timespec="seconds"), **record}
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    @staticmethod
    def _node(metadata: Any, tags: Any) -> str:
        """Which graph node / subagent produced this event."""
        if isinstance(metadata, dict):
            node = metadata.get("langgraph_node")
            if node:
                return str(node)
        for tag in tags or []:
            if isinstance(tag, str) and ":" in tag:
                return tag
        return "?"

    # ── callbacks ────────────────────────────────────────────────────────────
    @_guard
    def on_chat_model_start(
        self, serialized, messages, *, tags=None, metadata=None, **kwargs
    ):
        node = self._node(metadata, tags)
        rendered = []
        for msg_list in messages:
            for m in msg_list:
                rendered.append(
                    {
                        "role": getattr(m, "type", m.__class__.__name__),
                        "content": _stringify_content(getattr(m, "content", "")),
                    }
                )
        lines = [f"[{self._ts()}] [{node}] >> LLM input ({len(rendered)} msgs)"]
        for r in rendered:
            lines.append(f"    {r['role']}: {r['content']}")
        self._write_text("\n".join(lines))
        self._write_json({"event": "llm_start", "node": node, "messages": rendered})

    @_guard
    def on_llm_end(self, response, *, tags=None, metadata=None, **kwargs):
        node = self._node(metadata, tags)
        try:
            gen = response.generations[0][0]
        except (AttributeError, IndexError):
            return
        message = getattr(gen, "message", None)
        content = _stringify_content(
            getattr(message, "content", getattr(gen, "text", ""))
        )
        tool_calls = getattr(message, "tool_calls", None) or []
        lines = [f"[{self._ts()}] [{node}] << LLM output"]
        if content:
            lines.append(f"    {content}")
        for tc in tool_calls:
            args = json.dumps(tc.get("args", {}), default=str)
            lines.append(f"    tool_call: {tc.get('name')}({args})")
        self._write_text("\n".join(lines))
        self._write_json(
            {
                "event": "llm_end",
                "node": node,
                "content": content,
                "tool_calls": tool_calls,
            }
        )

    @_guard
    def on_tool_start(
        self, serialized, input_str, *, tags=None, metadata=None, **kwargs
    ):
        name = (serialized or {}).get("name", "tool")
        node = self._node(metadata, tags)
        self._write_text(f"[{self._ts()}] [{node}] -> TOOL {name}({input_str})")
        self._write_json(
            {"event": "tool_start", "node": node, "tool": name, "input": input_str}
        )

    @_guard
    def on_tool_end(self, output, *, tags=None, metadata=None, **kwargs):
        node = self._node(metadata, tags)
        text = _stringify_content(getattr(output, "content", output))
        self._write_text(f"[{self._ts()}] [{node}] <- TOOL result: {text}")
        self._write_json({"event": "tool_end", "node": node, "output": text})

    @_guard
    def on_chain_start(self, serialized, inputs, *, parent_run_id=None, **kwargs):
        # Only the root run (no parent) marks a task boundary; inner nodes/subgraphs
        # start constantly and would be noise.
        if parent_run_id is None:
            self._write_text(f"[{self._ts()}] ===== TASK START =====")
            self._write_json({"event": "task_start"})

    @_guard
    def on_chain_end(self, outputs, *, parent_run_id=None, **kwargs):
        if parent_run_id is None:
            self._write_text(f"[{self._ts()}] ===== TASK COMPLETE =====")
            self._write_json({"event": "task_end"})

    @_guard
    def on_llm_error(self, error, **kwargs):
        self._write_text(f"[{self._ts()}] !! LLM ERROR: {error}")
        self._write_json({"event": "llm_error", "error": str(error)})

    @_guard
    def on_tool_error(self, error, **kwargs):
        self._write_text(f"[{self._ts()}] !! TOOL ERROR: {error}")
        self._write_json({"event": "tool_error", "error": str(error)})
