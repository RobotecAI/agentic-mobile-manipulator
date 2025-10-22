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

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import field
from typing import Callable, List, Literal, Optional

import rclpy
from langchain_core.callbacks.base import BaseCallbackHandler
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from rai.agents.langchain.core import (
    Executor,
    create_megamind,
    get_initial_megamind_state,
)
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Message,
    wait_for_ros2_actions,
    wait_for_ros2_services,
    wait_for_ros2_topics,
)
from rclpy.node import Node
from robotec_kairos_ur10.msg import Anomaly

from rai_app.agents.callbacks import (
    AgentActionsCallback,
    AgentProgessCallback,
    OrchestratorTasksNotifier,
)
from rai_app.agents.context_providers import WarehouseContext
from rai_app.agents.tools import (
    CorrectBoxPositionTool,
    DescribeImageTool,
    HouseKeepTool,
    IsPackageDamagedTool,
    MoveFromCollectionToCollectionTool,
    MoveFromPoseToInspectionAreaTool,
    SortReturnedPackageTool,
    ThrowTrashOutTool,
)
from rai_app.config.prompts import (
    HOUSEKEEP_EXECUTOR_SYSTEM_PROMPT,
    IMAGE_ANALYSIS_EXECUTOR_SYSTEM_PROMPT,
    MEGAMIND_SYSTEM_PROMPT_TEMPLATE,
    MOVEMENT_EXECUTOR_SYSTEM_PROMPT,
)
from rai_app.control.kairos_controller import KairosController
from rai_app.environment import SceneManager
from rai_app.initialization.llms import get_llm_model, get_vlm_model
from scripts.populate_scene import load_rack_assignment

TOPICS_TO_WAIT_FOR: list[str] = ["/wrist_camera/camera_image_color"]
SERVICES_TO_WAIT_FOR: list[str] = [
    "/rai/moveit2/set_arm_joints",
    "/rai/moveit2/move_arm",
]
ACTIONS_TO_WAIT_FOR: list[str] = [
    "/rai/nav2/navigate_to_pose",
    "/rai/nav2/drive_on_heading",
    "/rai/nav2/spin",
    "/rai/nav2/follow_waypoints",
]


class TaskExecution(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: Literal["low", "high"] = "low"


class TaskSubscriber(Node):
    """ROS 2 subscriber node for orchestrator task intake.

    Parameters
    ----------
    connector : ROS2Connector
        Connector used to subscribe to ROS 2 topics.
    task_topics : list[str]
        Topics that publish user-initiated tasks.
    new_task_callback : Callable
        Callback executed when a task message is received.
    inspection_topics : list[str]
        Topics that publish inspection anomalies.
    inspection_callback : Callable
        Callback executed when an inspection anomaly arrives.

    Attributes
    ----------
    connector : ROS2Connector
        Connector instance used for topic subscriptions.
    new_task_callback : Callable
        Handler invoked for each new task message.
    inspection_callback : Callable
        Handler invoked for each inspection anomaly message.
    """

    def __init__(
        self,
        connector: ROS2Connector,
        task_topics: List[str],
        new_task_callback,
        inspection_topics: List[str],
        inspection_callback,
        housekeep_topics: List[str],
        housekeep_callback,
    ):
        super().__init__("task_subscriber")
        self.connector = connector
        self.new_task_callback = new_task_callback
        self.inspection_callback = inspection_callback
        self.housekeep_callback = housekeep_callback
        for topic in task_topics:
            self.add_task_topic(topic)
        for topic in inspection_topics:
            self.add_inspection_topic(topic=topic)
        for topic in housekeep_topics:
            self.add_housekeep_task_topic(topic=topic)

    def add_task_topic(self, topic: str):
        try:
            self.connector.register_callback(
                topic,
                self.new_task_callback,
                msg_type="std_msgs/msg/String",
            )
        except ValueError:
            logging.warning(f"Task topic: {topic} not found")

    def add_inspection_topic(self, topic: str):
        try:
            self.connector.register_callback(
                topic,
                self.inspection_callback,
                msg_type="robotec_kairos_ur10/msg/Anomaly",
            )
        except ValueError:
            logging.warning(f"Inspection topic: {topic} not found")

    def add_housekeep_task_topic(self, topic: str):
        try:
            self.connector.register_callback(
                topic,
                self.housekeep_callback,
                msg_type="std_msgs/msg/String",
            )
        except ValueError:
            logging.warning(f"Housekeep task topic: {topic} not found")

    def remove_topic(self, topic: str):
        self.connector.registered_callbacks.pop(topic)


class AgentOrchestrator:
    """Coordinate task execution across specialist agents.

    Parameters
    ----------
    connector : ROS2Connector
        ROS 2 communication interface used by the orchestrator.
    agent : CompiledStateGraph
        Compiled LangGraph agent responsible for task execution.
    task_topics : list[str]
        ROS 2 topics providing low-priority tasks.
    inspection_topics : list[str]
        ROS 2 topics providing high-priority inspection tasks.
    action_topic : str
        Topic where agent actions are published.
    initial_state_creator : Callable
        Factory that builds the initial agent state from a prompt.
    recurssion_limit : int
        Maximum LangGraph recursion depth.
    langchain_callbacks : list[BaseCallbackHandler]
        Callback handlers attached to agent execution.

    Attributes
    ----------
    current_task : TaskExecution | None
        Task currently under execution.
    current_task_future : asyncio.Task | None
        Async task representing the running agent invocation.
    high_prio_task_queue : asyncio.Queue
        Queue storing high-priority task requests.
    low_prio_task_queue : asyncio.Queue
        Queue storing low-priority task requests.

    running : bool
        Flag indicating whether the orchestrator loop should continue.
    """

    def __init__(
        self,
        connector: ROS2Connector,
        agent: CompiledStateGraph,
        task_topics: List[str],
        inspection_topics: List[str],
        housekeep_topics: List[str],
        action_topic: str,
        initial_state_creator: Callable,
        recurssion_limit: int,
        langchain_callbacks: List[BaseCallbackHandler],
    ):
        # low priority queue of tasks to execute
        self.low_prio_task_queue: asyncio.Queue[TaskExecution] = asyncio.Queue(
            maxsize=50
        )
        # high prio tasks will be executed first
        self.high_prio_task_queue: asyncio.Queue[TaskExecution] = asyncio.Queue(
            maxsize=50
        )
        self.task_subscriber = TaskSubscriber(
            connector=connector,
            task_topics=task_topics,
            new_task_callback=self.add_task,
            inspection_topics=inspection_topics,
            inspection_callback=self.add_inspection_task,
            housekeep_topics=housekeep_topics,
            housekeep_callback=self.add_housekeep_task,
        )

        self.initial_state_creator = initial_state_creator
        self.agent_graph = agent
        self.recurssion_limit = recurssion_limit
        self.agent_callbacks = langchain_callbacks
        self.agent = self.add_checkpointing_to_agent(self.agent_graph)

        self.connector = connector
        # for now we don't use change self.running but it can be useful
        # to shutdown orchestrator gracefully
        self.running = True
        self.current_task: Optional[TaskExecution] = None
        self.current_task_future = None
        self.stop: bool = False
        self.task_count = 0
        self.lock = threading.Lock()

        self.action_callback = AgentActionsCallback(
            connector=connector, topic=action_topic
        )
        self.notifier = OrchestratorTasksNotifier(
            connector=connector,
            current_task_topic="/orchestrator/current_task",
            tasks_queue_topic="/orchestrator/tasks_queue",
        )

    def notify_about_tasks(self):
        if self.current_task:
            self.notifier.send_main_task(self.current_task.prompt)
        else:
            self.notifier.send_main_task("No task currently...")

        # NOTE high prio tasks will be first in the message
        queue_tasks = []
        if not self.high_prio_task_queue.empty():
            for task in list(self.high_prio_task_queue._queue):
                queue_tasks.append(task.prompt)

        if not self.low_prio_task_queue.empty():
            for task in list(self.low_prio_task_queue._queue):
                queue_tasks.append(task.prompt)

        self.notifier.send_tasks_queue(queue_tasks)

    def add_inspection_task(self, msg: ROS2Message):
        # NOTE: All inspection tasks will be high prio
        anomaly: Anomaly = msg.payload
        pose = anomaly.pose
        # TODO  (jmatejcz) for now we classify box on the floor as trash
        # in the future this might need adjustment as well as prompt in inspection agent
        pose_prompt = (
            f" was detected at pose (x={pose.position}, y={pose.position.y}, z={pose.position.z},"
            f" qx={pose.orientation.x}, qy={pose.orientation.y}, qz={pose.orientation.z}, qw={pose.orientation.w}. "
        )
        if anomaly.obstacle_type == "box":
            prompt = "box" + pose_prompt
            prompt += "Move it to the inspection area."
            task_exe = TaskExecution(prompt=prompt, priority="high")
        elif anomaly.obstacle_type == "trash":
            prompt = "trash" + pose_prompt
            prompt += "Throw it out to the garbage bin."
            task_exe = TaskExecution(prompt=prompt, priority="high")
        else:
            logging.warning(
                f"Anomaly type {anomaly.obstacle_type} not valid for any action"
            )
            return
        with self.lock:
            try:
                self.high_prio_task_queue.put_nowait(task_exe)
                logging.info(f"Added high priority inspection task {task_exe.prompt}")
            except asyncio.QueueFull:
                logging.warning("Task queue is full, dropping task")

    def add_housekeep_task(self, msg: ROS2Message):
        prompt = msg.payload.data
        task_exe = TaskExecution(prompt=prompt, priority="high")
        with self.lock:
            try:
                self.high_prio_task_queue.put_nowait(task_exe)
                logging.info(f"Added high priority housekeep task {task_exe.prompt}")
            except asyncio.QueueFull:
                logging.warning("Task queue is full, dropping task")

    def add_task(self, msg: ROS2Message):
        """Queue a new low-priority task from a ROS 2 message.

        Parameters
        ----------
        msg : ROS2Message
            ROS 2 message containing the task prompt in ``msg.payload.data``.

        Returns
        -------
        None
            The task is enqueued for later execution.
        """
        # NOTE lower prio tasks
        task_exe = TaskExecution(prompt=msg.payload.data)
        with self.lock:
            try:
                self.low_prio_task_queue.put_nowait(task_exe)
                logging.info(f"Added task {task_exe.prompt}")
            except asyncio.QueueFull:
                logging.warning("Task queue is full, dropping task")

    def add_checkpointing_to_agent(
        self, agent: CompiledStateGraph
    ) -> CompiledStateGraph:
        # retrieve StateGraph
        agent_graph = agent.builder
        # Checkpointing
        # TODO (jmatejcz) can be done via sqlite in the future
        checkpointer = InMemorySaver()
        return agent_graph.compile(checkpointer=checkpointer)

    async def run_agent(
        self,
        task: TaskExecution,
    ):
        logging.info(f"Starting agent for task: {task.prompt}")
        initial_state = self.initial_state_creator(task.prompt)

        async for chunk in self.agent.astream(
            initial_state,
            config={
                "configurable": {"thread_id": task.thread_id},
                "recursion_limit": self.recurssion_limit,
                "callbacks": self.agent_callbacks,
                "tags": [f"task-id:{task.id}"],
            },
            subgraphs=True,
            stream_mode=["messages"],
        ):
            if self.stop:
                logging.info("Stopping the agent")
                break

            # await self.action_callback.process_stream_chunk(chunk)

    def spin_task_subscriber(self):
        rclpy.spin(self.task_subscriber)

    def task_notifier(self):
        """Publish task queue status periodically in a background thread.

        Returns
        -------
        None
            The loop runs until ``self.running`` is set to ``False``.
        """
        while self.running:
            with self.lock:
                self.notify_about_tasks()
            time.sleep(1)

    async def begin_high_prio_task(self):
        with self.lock:
            self.current_task = self.high_prio_task_queue.get_nowait()
            self.current_task_future = asyncio.create_task(
                self.run_agent(self.current_task)
            )

    async def begin_low_prio_task(self):
        with self.lock:
            self.current_task = self.low_prio_task_queue.get_nowait()
            self.current_task_future = asyncio.create_task(
                self.run_agent(self.current_task)
            )

    async def orchestrator_loop(self):
        """Run the main scheduling loop until shutdown is requested.

        Returns
        -------
        None
            Executes indefinitely, orchestrating task sequencing and agent
            invocation until ``self.running`` becomes ``False``.
        """

        sub_thread = threading.Thread(target=self.spin_task_subscriber, daemon=True)
        sub_thread.start()

        notification_thread = threading.Thread(target=self.task_notifier, daemon=True)
        notification_thread.start()

        while self.running:
            if not self.current_task:
                # No task running
                # First check for high prio tasks
                if not self.high_prio_task_queue.empty():
                    await self.begin_high_prio_task()

                # then for low prio tasks
                elif not self.low_prio_task_queue.empty():
                    await self.begin_low_prio_task()
            else:
                if self.current_task_future:
                    if self.current_task_future.done():
                        logging.info(f"Finished task: {self.current_task.prompt}")
                        self.current_task_future = None
                        self.current_task = None

            await asyncio.sleep(0.1)


def main():
    logging.getLogger("rai_agent")
    task_topics = ["/user_tasks"]
    housekeep_topics = ["/correct_boxes"]
    inspection_topics = ["/inspection_result"]
    connector = ROS2Connector()

    wait_for_ros2_actions(connector, ACTIONS_TO_WAIT_FOR)
    wait_for_ros2_topics(connector, TOPICS_TO_WAIT_FOR)
    wait_for_ros2_services(connector, SERVICES_TO_WAIT_FOR)

    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    kairos_controller = KairosController(
        connector=connector, scene_manager=scene_manager
    )

    llm = get_llm_model(config_name="megamind_agent")
    vlm = get_vlm_model(config_name="megamind_agent")

    move_from_coll_to_coll = MoveFromCollectionToCollectionTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    is_package_damaged_tool = IsPackageDamagedTool(
        connector=connector,
        namespace_value="",
        vlm=vlm,
    )
    throw_trash_out_tool = ThrowTrashOutTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    housekeep_tool = HouseKeepTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
        task_topic=housekeep_topics[0],
    )
    correct_box_tool = CorrectBoxPositionTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    move_to_inspection_are_tool = MoveFromPoseToInspectionAreaTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )

    sort_returned_package_tool = SortReturnedPackageTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
        vlm=vlm,
    )

    describe_image_tool = DescribeImageTool(
        connector=connector,
        vlm=vlm,
    )

    warehouse_context = WarehouseContext(scene_manager=scene_manager)
    entities = scene_manager.get_entities(name_filter="box")
    if entities:
        scene_manager.assign_entities_to_slots(entities)
    collection_names, item_types = load_rack_assignment(
        "scripts/resources/rack_assignment.csv"
    )

    scene_manager.assign_collections_to_item_types(collection_names, item_types)

    context = warehouse_context.get_context()

    executors = [
        Executor(
            name="housekeep",
            llm=llm,
            tools=[
                housekeep_tool,
                sort_returned_package_tool,
                correct_box_tool,
            ],
            system_prompt=HOUSEKEEP_EXECUTOR_SYSTEM_PROMPT.format(context=context),
        ),
        Executor(
            name="package_movement",
            llm=llm,
            tools=[
                move_from_coll_to_coll,
                move_to_inspection_are_tool,
                throw_trash_out_tool,
            ],
            system_prompt=MOVEMENT_EXECUTOR_SYSTEM_PROMPT.format(context=context),
        ),
        Executor(
            name="image_analysis",
            llm=llm,
            tools=[is_package_damaged_tool, describe_image_tool],
            system_prompt=IMAGE_ANALYSIS_EXECUTOR_SYSTEM_PROMPT,
        ),
    ]

    executor_overview = ""
    for executor in executors:
        executor_overview += (
            f"- {executor.name} specialist can use the following tools: \n"
        )
        for tool in executor.tools:
            executor_overview += f"    -{tool.name}: {tool.description}\n"
    megamind_system_prompt = MEGAMIND_SYSTEM_PROMPT_TEMPLATE.format(
        executor_overview=executor_overview, context=context
    )

    agent = create_megamind(
        megamind_system_prompt=megamind_system_prompt,
        megamind_llm=llm,
        executors=executors,
    )

    langfuse_handler = CallbackHandler()

    ros2_callback = AgentProgessCallback(connector)
    orchestrator = AgentOrchestrator(
        connector=connector,
        agent=agent,
        task_topics=task_topics,
        inspection_topics=inspection_topics,
        housekeep_topics=housekeep_topics,
        action_topic="/agent/current_action",
        initial_state_creator=get_initial_megamind_state,
        recurssion_limit=100,
        langchain_callbacks=[langfuse_handler, ros2_callback],
    )
    asyncio.run(orchestrator.orchestrator_loop())


if __name__ == "__main__":
    main()
