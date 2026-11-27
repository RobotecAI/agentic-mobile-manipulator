# Copyright (C) 2026 Advanced Micro Devices, Inc.
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
#
# Developed by Robotec.ai sp. z o.o.

"""The /agent/events stream the HMI reads (no ROS needed: the connector is faked)."""

import asyncio
import json
import uuid
from types import SimpleNamespace

from langchain_core.messages import AIMessageChunk, ToolMessage

from rai_app.agents.callbacks import AgentActionsCallback, AgentProgressCallback


class FakeConnector:
    def __init__(self):
        self.sent = []

    def send_message(self, message, msg_type, target):
        self.sent.append((target, msg_type, message.payload))

    def events(self):
        return [json.loads(p["data"]) for t, _, p in self.sent if t == "/agent/events"]


def test_tool_start_and_end_pair_by_run_id():
    connector = FakeConnector()
    callback = AgentProgressCallback(connector)
    run_id = uuid.uuid4()
    metadata = {"langgraph_checkpoint_ns": "housekeep:abc|tools:def"}
    asyncio.run(
        callback.on_tool_start(
            {"name": "housekeep_tool"},
            "{'rack': 'J01'}",
            run_id=run_id,
            metadata=metadata,
            inputs={"rack": "J01"},
        )
    )
    asyncio.run(
        callback.on_tool_end(
            ToolMessage(content="2 boxes moved", tool_call_id="x"), run_id=run_id
        )
    )

    start, end = connector.events()
    assert start["type"] == "tool_start" and start["node"] == "housekeep"
    assert start["tool"] == "housekeep_tool" and start["args"] == {"rack": "J01"}
    assert end["type"] == "tool_end" and end["run_id"] == start["run_id"]
    assert end["output"] == "2 boxes moved" and end["status"] == "ok"


def test_llm_end_reports_token_usage():
    connector = FakeConnector()
    callback = AgentProgressCallback(connector)
    run_id = uuid.uuid4()
    asyncio.run(
        callback.on_chat_model_start(
            run_id=run_id, metadata={"langgraph_checkpoint_ns": "megamind:1"}
        )
    )
    response = SimpleNamespace(
        llm_output={"token_usage": {"prompt_tokens": 1900, "completion_tokens": 214}}
    )
    asyncio.run(callback.on_llm_end(response, run_id=run_id))

    (event,) = connector.events()
    assert (event["type"], event["node"], event["tokens_in"], event["tokens_out"]) == (
        "llm_end",
        "megamind",
        1900,
        214,
    )


def test_stream_chunks_become_text_and_thinking_events():
    connector = FakeConnector()
    callback = AgentActionsCallback(connector, topic="/agent/current_action")
    chunk = AIMessageChunk(
        content="Moving the box.",
        additional_kwargs={"reasoning_content": "Box is misplaced."},
    )
    asyncio.run(
        callback.process_stream_chunk(
            (("package_movement:run7",), "messages", (chunk, {}))
        )
    )

    kinds = [
        (e["type"], e["node"], e["run_id"], e["chunk"]) for e in connector.events()
    ]
    assert kinds == [
        ("thinking", "package_movement", "run7", "Box is misplaced."),
        ("text", "package_movement", "run7", "Moving the box."),
    ]
