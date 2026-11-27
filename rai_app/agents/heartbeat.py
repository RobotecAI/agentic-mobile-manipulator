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

"""Agent liveness for the HMI and the HMI-facing event stream.

- ``/agents/heartbeat`` (``std_msgs/Header``): every agent process publishes its name in
  ``frame_id`` every ``HEARTBEAT_PERIOD_S``.
- ``/agent/events`` (``std_msgs/String``): one JSON object per agent event; see
  ``publish_agent_event`` and docs/setup_hmi.md for the fields.
"""

import json
import logging
import threading
import time
from typing import Any

from rai.communication.ros2 import ROS2Connector, ROS2Message

HEARTBEAT_TOPIC = "/agents/heartbeat"
HEARTBEAT_PERIOD_S = 2.0
EVENTS_TOPIC = "/agent/events"
# Tool outputs can be large (scene dumps); the HMI only needs the gist.
MAX_EVENT_TEXT = 2000


def start_heartbeat(connector: ROS2Connector, name: str) -> threading.Thread:
    """Publish ``name`` on /agents/heartbeat from a daemon thread until the process exits."""

    def beat():
        while True:
            try:
                connector.send_message(
                    message=ROS2Message(payload={"frame_id": name}),
                    msg_type="std_msgs/msg/Header",
                    target=HEARTBEAT_TOPIC,
                )
            except Exception as exc:  # noqa: BLE001 - liveness must never crash the agent
                logging.debug(f"heartbeat for {name} failed: {exc}")
            time.sleep(HEARTBEAT_PERIOD_S)

    thread = threading.Thread(target=beat, name=f"heartbeat-{name}", daemon=True)
    thread.start()
    return thread


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_EVENT_TEXT:
        return value[:MAX_EVENT_TEXT] + "…"
    return value


def publish_agent_event(connector: ROS2Connector, type: str, **fields: Any) -> None:
    """Publish one event on /agent/events. Never raises.

    Types and fields: ``task_start``/``task_end`` (task, status), ``text``/``thinking``
    (node, run_id, chunk), ``tool_start`` (node, run_id, tool, args), ``tool_end``
    (run_id, tool, output, status), ``llm_end`` (node, tokens_in, tokens_out),
    ``steps`` (steps).
    """
    event = {"type": type, "t": time.time(), **{k: _clip(v) for k, v in fields.items()}}
    try:
        connector.send_message(
            message=ROS2Message(payload={"data": json.dumps(event, default=str)}),
            msg_type="std_msgs/msg/String",
            target=EVENTS_TOPIC,
        )
    except Exception as exc:  # noqa: BLE001 - the HMI stream must never break the agent
        logging.debug(f"agent event {type} not published: {exc}")
