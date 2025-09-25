import asyncio
import logging
import threading
import uuid
from pydantic import BaseModel
from dataclasses import field
from collections import deque
from typing import Callable, Dict, List, Optional, Deque
from langgraph.checkpoint.memory import InMemorySaver
import rclpy
from langchain_core.callbacks.base import BaseCallbackHandler
from langgraph.graph.state import CompiledStateGraph
from rclpy.node import Node
from rclpy.subscription import Subscription

from rai.communication.ros2 import ROS2Connector, ROS2Message
from context_providers import WarehouseContext


class TaskExecution(BaseModel):
    prompt: str = ""
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_paused: bool = False


class TaskSubscriber(Node):
    """ROS2 node that subscribes to multiple task topics"""

    def __init__(self, connector: ROS2Connector, topics: List[str], new_task_callback):
        super().__init__("task_subscriber")
        self.connector = connector
        self.topic_subscriptions: Dict[str, Subscription] = {}
        self.new_task_callback = new_task_callback
        for topic in topics:
            self.add_topic(topic)

    def add_topic(self, topic: str):
        try:
            self.connector.register_callback(topic, self.new_task_callback)
        except ValueError:
            logging.warning(f"{topic} not found")

    def remove_topic(self, topic: str):
        self.connector.registered_callbacks.pop(topic)


class AgentOrchestrator:
    """Main orchestrator for managing agents and tasks"""

    def __init__(
        self,
        connector,
        agent: CompiledStateGraph,
        task_topics: List[str],
        initial_state_creator: Callable,
        recurssion_limit: int,
        agent_callbacks: List[BaseCallbackHandler],
    ):
        # low priority queue of tasks to execute
        self.task_queue: asyncio.Queue[TaskExecution] = asyncio.Queue(maxsize=20)
        # when task is interrupted mid execution,
        # the checkpoint is saved and stored. The task is
        # put onto paused task lifo queue and will be resumed
        # when the interrupting task is done
        self.pasued_tasks_queue: Deque[TaskExecution] = deque(maxlen=10)
        self.task_subscriber = TaskSubscriber(
            connector=connector, topics=task_topics, new_task_callback=self.add_task
        )

        self.initial_state_creator = initial_state_creator
        self.agent_graph = agent
        self.recurssion_limit = recurssion_limit
        self.agent_callbacks = agent_callbacks
        self.agent = self.add_checkpointing_to_agent(self.agent_graph)

        self.connector = ROS2Connector()
        # for now we don't use change self.running but it can be useful
        # to shutdown orchestrator gracefully
        self.running = True
        self.current_task: Optional[TaskExecution] = None
        self.high_prio_task: Optional[TaskExecution] = None
        self.current_task_future = None
        self.stop: bool = False
        self.task_count = 0
        self.lock = threading.Lock()

    def add_task(self, msg: ROS2Message):
        """Add a new task to the queue"""
        logging.info(f"Adding task {msg.payload.data}")

        # TODO (jmatejcz) when new msg type drops prio will be extracted from msg
        # for now it is mocked that every second msg is high prio
        task_exe = TaskExecution(prompt=msg.payload.data)

        # high_prio task is changed both in this
        # funtion which is a callback of ros thread
        # and in the main ochestrator loop
        # additionally this funtion can be accesed by multiple ros2 callbacks
        with self.lock:
            if self.task_count % 2 == 0:
                try:
                    self.task_queue.put_nowait(task_exe)
                except asyncio.QueueFull:
                    logging.warning("Task queue is full, dropping task")
            else:
                logging.info("High prio task recieved")

                self.high_prio_task = task_exe

            self.task_count += 1

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

        async for subgraph, state in self.agent.astream(
            initial_state,
            config={
                "configurable": {"thread_id": task.thread_id},
                "recursion_limit": self.recurssion_limit,
                "callbacks": self.agent_callbacks,
            },
            subgraphs=True,
        ):
            if self.stop:
                logging.info("Stopping the agent")
                break

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
                        logging.info(f"task {self.current_task.prompt}")
                        current_task_future = asyncio.create_task(
                            self.run_agent(self.current_task)
                        )
                        logging.info("after creating task")
                    except TimeoutError:
                        await asyncio.sleep(1)
                        continue

            if current_task_future.done():
                current_task_future = None
                self.current_task = None
                ...
                # TODO (jmatejcz) send message or somth
            await asyncio.sleep(0.01)


if __name__ == "__main__":
    from typing import Optional
    from rai.communication.ros2 import ROS2Connector
    from pydantic import BaseModel
    from langchain_openai import ChatOpenAI
    from langchain_ollama import ChatOllama
    from langfuse.callback import CallbackHandler
    import logging
    from tools import (
        NavigateToSlotSyncTool,
        IsPackageDamagedTool,
        MoveFromCollectionToCollectionTool,
    )
    from scripts.kairos_controller import KairosController
    from scripts.scene_manager import SceneManager

    from rai.agents.langchain.core import (
        create_megamind,
        Executor,
        get_initial_megamind_state,
    )

    logging.getLogger("rai_agent")
    connector = ROS2Connector()
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    kairos_controller = KairosController(connector=connector)

    agent_model = "gpt-4o"
    agent_vendor = "openai"

    llm = (
        ChatOpenAI(
            model=agent_model,
            streaming=True,
        )
        if agent_vendor == "openai"
        else ChatOllama(
            model=agent_model,
            reasoning=False,
        )
    )

    move_from_coll_to_coll = MoveFromCollectionToCollectionTool(
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
        namespace_value="",
        llm=llm,
    )

    movement_system_prompt = """You are a movement specialist robot agent.
Your role is to handle navigating to slots and moving objects from collection to collection using tools."""

    detection_system_prompt = """You are a detection specialist agent.
Your role is to identify object state using tools."""

    megamind_system_prompt = """You are a mobile robot operating in a warehouse environment for pick-and-place operations.
You manage specialists to whom you will delegate tasks:
- Movement specialist can move object from a collection to collection (table, racks) and navigate to given slot.
- Detection specialist can identify the state of the package at current slot. 
Use detection agent only when specificly asked about object state, for example if it is damaged. 

For proper execution of an objective you NEED to know:
- what objects are you meant to move
- from where to pick them
- where to place them
IF you CAN'T figure it out on your own, ask user for clarification.
"""

    executors = [
        Executor(
            name="movement",
            llm=llm,
            tools=[move_from_coll_to_coll, navigation_tool],
            system_prompt=movement_system_prompt,
        ),
        Executor(
            name="detection",
            llm=llm,
            tools=[vlm_tool],
            system_prompt=detection_system_prompt,
        ),
    ]
    warehouse_context = WarehouseContext(scene_manager=scene_manager)
    # TODO create megamind has to return not compiled StateGraph
    # because checkpointing has to be added before compiling
    # currently rai-core implements create_megamind which returns compiled graph
    # so temporarly we have to  change installed package
    agent = create_megamind(
        megamind_system_prompt=megamind_system_prompt,
        megamind_llm=llm,
        executors=executors,
        context_providers=[warehouse_context],
    )

    langfuse_handler = CallbackHandler()
    task_topics = ["/safety_issues", "/inspection_issues", "/user_tasks"]
    orchestrator = AgentOrchestrator(
        connector=connector,
        agent=agent,
        task_topics=task_topics,
        initial_state_creator=get_initial_megamind_state,
        recurssion_limit=100,
        agent_callbacks=[langfuse_handler],
    )
    asyncio.run(orchestrator.orchestrator_loop())
