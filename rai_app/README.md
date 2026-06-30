# Orchestrator and Megamind Agent System Documentation

## Overview

This system implements a hierarchical multi-agent architecture for warehouse automation tasks. It consists of two main components:

1. **Agent Orchestrator**: Manages task execution, queuing, and prioritization
2. **Megamind Agent**: Coordinates specialized executor agents to complete complex tasks

## Architecture

![Orchestrator and Megamind Agent System Architecture](../docs/images/orchestrator_megamind_scheme.png)

## Agent Orchestrator

The orchestrator manages the execution of tasks from multiple sources, handles task prioritization, and supports task interruption and resumption.

### Key Features

- **Multi-source task intake** via ROS2 topics
- **Task queuing** with configurable queue sizes
- **Task interruption and resumption** with checkpoint saving
- **Priority-based execution** (high priority tasks can interrupt current tasks)
- **Asynchronous task execution** with proper resource management

### Core Classes

#### TaskExecution

Represents a single task to be executed:

- `id`
- `prompt`: Task description
- `thread_id`: Checkpoint thread identifier for langchain

#### TaskSubscriber

ROS2 node that subscribes to multiple topics:

- General task topics for user commands
- Inspection topics for anomaly detection

#### AgentOrchestrator

Main orchestration engine with:

- Task queue management (low and high prio)
- Agent execution control
- Checkpointing support via LangGraph
- Progress callbacks and action publishing

### Task Flow

1. Tasks arrive via ROS2 topics
2. Tasks are queued based on priority
3. Orchestrator executes tasks sequentially
4. High-priority tasks can interrupt current execution
5. Interrupted tasks are saved and resumed later

## Megamind Agent System

Megamind is a hierarchical planning agent that delegates tasks splits them into steps to executor agents.

### Architecture

#### Megamind (Coordinator)

- Plans task execution strategy
- Delegates subtasks to specialized executors
- Tracks completion status
- Manages overall task flow

#### Executors (Specialists)

Specialized agents with specific capabilities:

1. **Housekeep Executor**: Organizes warehouse, sorts packages, corrects positions
2. **Package Movement Executor**: Handles physical movement of items
3. **Image Analysis Executor**: Analyzes images for damage detection

### State Management

The system uses `MegamindState` to track:

- `original_task`: Initial user request
- `steps_done`: Completed step
- `step`: Current step
- `step_success`: Success status and explanation
- `step_messages`: Execution history

### Execution Flow

1. **Planning Phase**

   - Megamind analyzes the task
   - Creates next step
   - Selects appropriate executor
   - If task completed, returns to user

2. **Delegation Phase**

   - Handoff tool transfers control to executor
   - Executor performs given step
   - Results are analyzed

3. **Evaluation Phase**
   - Success analyzer evaluates completion and explains what happened
   - State is updated with these results
   - These results are available during planning phase as additional information

### Task Topics

- `/user_tasks`: General user commands
- `/inspection_result`: Anomaly detection results

## Task Types

### User Tasks

Direct commands from users:

- "Sort all returned packages"
- "Move box from shelf A to shelf B"
- "Inspect package for damage"

### Inspection Tasks

Automatically generated from anomaly detection:

- Box on floor → Move to inspection area
- Trash detected → Dispose in garbage bin

## Other Features

### Checkpointing

- In-memory checkpointing for task resumption
- Thread-based state isolation
- Automatic state recovery after interruption

### Context Providers

External context injection for better planning, like layout of the warehouse

### Callbacks

- **AgentActionsCallback**: Publishes current actions
- **AgentProgressCallback**: Tracks execution progress
- **Langfuse Integration**: Monitoring by langfuse

## Topic Communication

Agent actions topic-> /agent/current_action , rai_interfaces/msg/HRIMessage - Can be tokens or tool calls
Steps already done during this task -> /agent/past_steps , std_msgs/msg/String
current task topic -> /orchestrator/current_task, std_msgs/msg/String
tasks queue topic-> /orchestrator/tasks_queue, std_msgs/msg/String

## Setup and Run

1. Follow the setup instructions [here](../docs/setup_single_machine.md).
2. Setup your vendor and model in config [here](../config.toml). If using default openai, remember to set OPENAI_API_KEY env.
3. Launch the simulation:

```bash
pixi run sim
```

4. Launch the robotic stack:

```bash
pixi run stack
```

5. Spawn objects in HMI, choosing from different scenarios

6. Run orchestrator:

```bash
pixi run orchestrator
```

7. Send tasks via HMI
