import asyncio
import logging
import threading
import uuid
from collections import deque
from dataclasses import field
from typing import Callable, Deque, List, Optional

import rclpy
from agent_callbacks import AgentActionsCallback, AgentProgessCallback
from context_providers import WarehouseContext
from langchain_core.callbacks.base import BaseCallbackHandler
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from llms import get_model
from pydantic import BaseModel
from rai.agents.langchain.core import (
    Executor,
    create_megamind,
    get_initial_megamind_state,
)
from rai.communication.ros2 import ROS2Connector, ROS2Message
from rclpy.node import Node
from robotec_kairos_ur10.msg import Anomaly
from tools import (
    CorrectBoxPositionTool,
    HouseKeepTool,
    IsPackageDamagedTool,
    MoveFromCollectionToCollectionTool,
    MoveFromPoseToInspectionAreaTool,
    ThrowTrashOutTool,
)

from scripts.kairos_controller import KairosController
from scripts.populate_scene import load_item_type_assignment_file
from scripts.scene_manager import SceneManager


class TaskExecution(BaseModel):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_paused: bool = False


class TaskSubscriber(Node):
    """ROS2 node that subscribes to multiple task topics"""

    def __init__(
        self,
        connector: ROS2Connector,
        task_topics: List[str],
        new_task_callback,
        inspection_topics: List[str],
        inspection_callback,
    ):
        super().__init__("task_subscriber")
        self.connector = connector
        self.new_task_callback = new_task_callback
        self.inspection_callback = inspection_callback
        for topic in task_topics:
            self.add_task_topic(topic)
        for topic in inspection_topics:
            self.add_inspection_topic(topic=topic)

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

    def remove_topic(self, topic: str):
        self.connector.registered_callbacks.pop(topic)


class AgentOrchestrator:
    """Main orchestrator for managing agents and tasks"""

    def __init__(
        self,
        connector: ROS2Connector,
        agent: CompiledStateGraph,
        task_topics: List[str],
        inspection_topics: List[str],
        action_topic: str,
        initial_state_creator: Callable,
        recurssion_limit: int,
        langchain_callbacks: List[BaseCallbackHandler],
    ):
        # low priority queue of tasks to execute
        self.task_queue: asyncio.Queue[TaskExecution] = asyncio.Queue(maxsize=50)
        # when task is interrupted mid execution,
        # the checkpoint is saved and stored. The task is
        # put onto paused task lifo queue and will be resumed
        # when the interrupting task is done
        self.pasued_tasks_queue: Deque[TaskExecution] = deque(maxlen=10)
        self.task_subscriber = TaskSubscriber(
            connector=connector,
            task_topics=task_topics,
            new_task_callback=self.add_task,
            inspection_topics=inspection_topics,
            inspection_callback=self.add_inspection_task,
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
        self.high_prio_task: Optional[TaskExecution] = None
        self.current_task_future = None
        self.stop: bool = False
        self.task_count = 0
        self.lock = threading.Lock()

        self.action_callback = AgentActionsCallback(
            connector=connector, topic=action_topic
        )

    def add_inspection_task(self, msg: ROS2Message):
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
            task_exe = TaskExecution(prompt=prompt)
        elif anomaly.obstacle_type == "trash":
            prompt = "trash" + pose_prompt
            prompt += "Throw it out to the garbage bin."
            task_exe = TaskExecution(prompt=prompt)
        else:
            logging.warning(
                f"Anomaly type {anomaly.obstacle_type} not valid for any action"
            )
            return
        with self.lock:
            try:
                self.task_queue.put_nowait(task_exe)
                logging.info(f"Added inspection task {task_exe.prompt}")
            except asyncio.QueueFull:
                logging.warning("Task queue is full, dropping task")

    def add_task(self, msg: ROS2Message):
        """Add a new task to the queue"""
        # TODO (jmatejcz) when new msg type drops prio will be extracted from msg
        # for now no high prio tasks
        task_exe = TaskExecution(prompt=msg.payload.data)
        with self.lock:
            try:
                self.task_queue.put_nowait(task_exe)
                logging.info(f"Added task {task_exe.prompt}")
            except asyncio.QueueFull:
                logging.warning("Task queue is full, dropping task")

    async def interrupt_current_task(self):
        """
        Interrupt currently running task.
        Interuppted task will be apped to deque as paused.
        """
        if not self.current_task:
            return
        if self.current_task_future and not self.current_task_future.done():
            logging.warning("Interrupting current task")
            await asyncio.wait_for(self.current_task_future, timeout=3.0)
            try:
                self.current_task.is_paused = True
                self.pasued_tasks_queue.appendleft(self.current_task)
            except asyncio.QueueFull:
                logging.warning("Limit of pasued tasks reached. removing the oldest")
                self.pasued_tasks_queue.pop()
                self.pasued_tasks_queue.appendleft(self.current_task)
        self.current_task = None

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
        if task.is_paused:
            logging.info(f"Resuming task: {task.prompt}")
            # no initial state when resuming
            initial_state = None
        else:
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

            await self.action_callback.process_stream_chunk(chunk)

    def spin_task_subscriber(self):
        rclpy.spin(self.task_subscriber)

    async def orchestrator_loop(self):
        """Main orchestrator loop"""

        sub_thread = threading.Thread(target=self.spin_task_subscriber, daemon=True)
        sub_thread.start()

        current_task_future = None

        while self.running:
            # check for high prio task with mutex
            high_prio_task = None
            with self.lock:
                if self.high_prio_task:
                    high_prio_task = self.high_prio_task
                    self.high_prio_task = None

            # if there is high prio task, interruct current one
            # adn run high prio
            if high_prio_task:
                if current_task_future:
                    await self.interrupt_current_task()

                self.current_task = high_prio_task
                current_task_future = asyncio.create_task(
                    self.run_agent(self.current_task)
                )
            elif current_task_future is None:
                # if there is no high prio
                # and no task running
                # first check for paused tasks to resume
                if self.pasued_tasks_queue:
                    self.current_task = self.pasued_tasks_queue.popleft()
                    current_task_future = asyncio.create_task(
                        self.run_agent(self.current_task)
                    )
                # if no paused get the next from queue
                else:
                    try:
                        self.current_task = await asyncio.wait_for(
                            self.task_queue.get(), timeout=1.0
                        )
                        current_task_future = asyncio.create_task(
                            self.run_agent(self.current_task)
                        )
                    except TimeoutError:
                        await asyncio.sleep(1)
                        continue

            if current_task_future.done():
                current_task_future = None
                self.current_task = None
                ...
                # TODO (jmatejcz) send message or somth
            await asyncio.sleep(0.01)


def main():
    logging.getLogger("rai_agent")
    task_topics = ["/user_tasks", "/correct_boxes"]
    inspection_topics = ["/inspection_result"]
    connector = ROS2Connector()
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    kairos_controller = KairosController(
        connector=connector, scene_manager=scene_manager
    )

    llm = get_model(model="qwen3:14b", vendor="ollama", reasoning=True)

    move_from_coll_to_coll = MoveFromCollectionToCollectionTool(
        connector=connector,
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
    )
    vlm_tool = IsPackageDamagedTool(
        connector=connector,
        namespace_value="",
        llm=llm,
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
        task_topic=task_topics[0],
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
    warehouse_context = WarehouseContext(scene_manager=scene_manager)
    entities = scene_manager.get_entities(name_filter="box")
    if entities:
        scene_manager.assign_entities_to_slots(entities)
    collection_names, item_types = load_item_type_assignment_file(
        "rai_app/resources/rack_assignment.csv"
    )

    scene_manager.assign_collections_to_item_types(collection_names, item_types)

    context = warehouse_context.get_context()
    movement_system_prompt = f"""You are a movement specialist robot agent.
    Your role is to handle moving objects from collection to collection, throwing out trash,
    moving to inspection area or correcting placements.
    using tools.
    {context}
    """

    detection_system_prompt = """You are a detection specialist agent.
    Your role is to do housekeeping and identify objects state using tools."""

    megamind_system_prompt = """You are a mobile robot operating in a warehouse environment for pick-and-place operations.
    You manage specialists to whom you will delegate tasks:
    - Movement specialist can move object from a collection to collection (table, racks, bins, inspection areas),
    throw out trash, correct boxes placement 
    - Detection specialist can do housekeeping and identify the state of the package at current slot.

    Specialist does not have access to exact positions so be sure to always pass exact pose when it is provided.
    """

    executors = [
        Executor(
            name="movement",
            llm=llm,
            tools=[
                move_from_coll_to_coll,
                throw_trash_out_tool,
                correct_box_tool,
                move_to_inspection_are_tool,
            ],
            system_prompt=movement_system_prompt,
        ),
        Executor(
            name="detection",
            llm=llm,
            tools=[vlm_tool, housekeep_tool],
            system_prompt=detection_system_prompt,
        ),
    ]

    # TODO create megamind has to return not compiled StateGraph
    # because checkpointing has to be added before compiling
    # currently rai-core implements create_megamind which returns compiled graph
    # so temporarly we have to  change installed package
    agent = create_megamind(
        megamind_system_prompt=megamind_system_prompt,
        megamind_llm=llm,
        executors=executors,
        # context_providers=[warehouse_context],
    )

    langfuse_handler = CallbackHandler()

    ros2_callback = AgentProgessCallback(connector)
    orchestrator = AgentOrchestrator(
        connector=connector,
        agent=agent,
        task_topics=task_topics,
        inspection_topics=inspection_topics,
        action_topic="/agent/current_action",
        initial_state_creator=get_initial_megamind_state,
        recurssion_limit=100,
        langchain_callbacks=[langfuse_handler, ros2_callback],
    )
    asyncio.run(orchestrator.orchestrator_loop())


if __name__ == "__main__":
    main()
