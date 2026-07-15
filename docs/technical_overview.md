# Technical Overview

This demo is built on top of RobotecAI's RAI framework, combining the open-source agent stack with the warehouse simulation assets to orchestrate LangChain-driven task planning, ROS 2 control, and perception workflows.[^rai-gh][^rai-docs]

## Platform Stack

- **Agent layer (`rai_app/agents/`)**: Wraps RAI's Megamind coordinator with executor agents for housekeeping, package movement, and image analysis. LangGraph checkpointing lets the orchestrator pause, resume, and reprioritize queued tasks while streaming status back to ROS 2 topics.
- **Tooling layer (`rai_app/agents/tools.py`)**: Bridges agent intents to robot skills - navigation, manipulation, anomaly triage-through ROS 2 actions, services, and scene queries. Warehouse context providers preload rack assignments and slot metadata so the planners can reason about inventory layout.
- **ROS 2 integration (`rai_app/environment/`, `rai_app/control/`)**: `SceneManager` in environment manages O3DE entities and slot metadata, while `KairosController` and other control modules handle MoveIt planning and Nav2 trajectories. These expose high-level routines (pick-and-place, rotate, throw to bin) that the agents call via tools.
- **Perception services**: The inspection agent subscribes to camera feeds, triggers a VLM anomaly classifier, and publishes high-priority tasks. The safety agent runs a regulation-focused VLM + RAG pipeline to log and broadcast violations.

## Runtime Flow

1. **Spin up ROS 2 stack**: Launch navigation, manipulation, and perception nodes alongside the simulation. `SceneManager` seeds racks/tables according to CSV resources and keeps entity-slot assignments in sync.
2. **Start the orchestrator**: The main agent process subscribes to `/user_tasks` and `/inspection_result`, initializes the Megamind graph, and begins the event loop that prioritizes, checkpoint-resumes, or dispatches tasks.
3. **Execute tasks**: When a task is dequeued, Megamind plans subtasks, selects the right executor, and invokes tools. Tool calls translate into ROS 2 actions (Nav2 navigation, MoveIt2 manipulation) or service calls (scene updates, anomaly reporting).
4. **Monitor feedback**: Agent callbacks stream reasoning steps and tool invocations to `/agent/current_action`, `/agent/past_steps`, and orchestrator status topics for HMI/diagnostics.

## Deployment Notes

- **Configuration**: `config.toml` defines the LLM/VLM endpoints used by the executors, inspection agent, and safety agent. Environment variables supply API credentials when the stack is run outside development.
- **Extensibility**: New task flows slot in by creating additional executor nodes or ROS 2 tools; the orchestrator automatically handles scheduling as long as tasks are published to the monitored topics.

[^rai-gh]: RAI repository, https://github.com/RobotecAI/rai
[^rai-docs]: RAI documentation, https://robotecai.github.io/rai/
