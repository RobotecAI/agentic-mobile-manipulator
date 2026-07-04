# Agentic Mobile Manipulator: Repository & Architecture Overview

This document provides a comprehensive guide to navigating the **Agentic Mobile Manipulator** repository. It explains the project structure, key components, and how they interact to create an autonomous warehouse robot demo.

## 1. Repository Structure

The repository is organized into several key directories:

### Core Logic

- **`rai_app/`**: The "brain" of the system. Contains the Python-based Agentic AI logic.
  - **`agents/`**: Implementations of the various agents (Orchestrator, Inspection, Safety, Navigation, Manipulation).
  - **`control/`**: Interfaces that bridge the AI agents with the ROS 2 control systems.
  - **`warehouse_regulations_agent/`**: Implements the RAG (Retrieval-Augmented Generation) system for safety compliance, including the vector database tools.
  - **`config/`**: Prompt definitions for the agents.

### Robotics & Middleware

- **`ros2_ws/`**: The "nervous system". A standard ROS 2 workspace containing custom packages.
  - **`mobile_manipulator_hmi/`**: A Qt-based Human-Machine Interface (HMI) for operators to interact with the robot.
  - **`robotec_kairos_ur10/`**: Robot configuration, description files, and maps for the Robotnik Kairos platform.
  - **`custom_adjustment_nav2/`**: Custom behavior tree nodes for the Nav2 navigation stack.

### Infrastructure & Simulation

- **`docker/`**: Deployment files for AMD GPU + AMD Ryzen™ AI. A layered build (`ros2` → `o3de` → `demo`) produces a single container that runs the whole demo via `pixi run demo`. See the [Quickstart Guide](./quickstart.md).
- **`project_gems/`**: Assets and configurations for the **O3DE (Open 3D Engine)** simulation environment.
- **`config.toml`**: The central configuration file for the agents' LLMs and VLMs. Each endpoint declares a local backend — CPU/GPU via llama.cpp (Vulkan) or the **AMD Ryzen™ AI NPU** via FastFlowLM — so models can be moved across CPU, GPU and NPU in one place.

## 2. Key Components

### The Agentic System (`rai_app`)

The system is built on a multi-agent architecture orchestrated by a "MegaMind" agent.

- **Orchestrator (MegaMind)**: Uses `LangGraph` to manage state and delegate tasks to specialized sub-agents. It parses user commands and decides which tool or agent to invoke.
- **Inspection Agent**: Utilizes Vision-Language Models (VLM) to analyze camera feeds and detect anomalies (e.g., spills, obstacles).
- **Safety Agent**: Combines VLM analysis with a RAG system (`warehouse_regulations_agent`) to cross-reference visual data with a database of safety regulations (e.g., OSHA standards).
- **Control Agents**: The `nav2_agent` and `moveit2_agent` translate high-level plans into specific ROS 2 actions for navigation and arm manipulation.

### The ROS 2 Stack

- **HMI**: Provides a visual interface to see the robot's status, chat with the agent, and issue commands.
- **Simulation Interface**: The stack communicates with the O3DE simulation via standard ROS 2 interfaces, allowing the software to treat the simulation exactly like real hardware ("Hardware-in-the-Loop" style).

## 3. Configuration (`config.toml`)

This file is the control center for your model backend. You can define:

- **LLM/VLM Endpoints**: Define the model, backend, and port each agent uses.
- **Model Parameters**: Adjust reasoning capabilities or temperature for specific agents.
- **RAG Settings**: Configure the embedding models used by the Safety Agent.

## 4. Workflow

1.  **User Input**: The user sends a command via the HMI (e.g., "Check that pallet").
2.  **Orchestrator**: The message is received by the `rai_app`, where the Orchestrator analyzes the intent.
3.  **Agent Delegation**: The Orchestrator activates the appropriate agent (e.g., Inspection Agent).
4.  **Perception & Reasoning**: The agent may capture an image from the simulation, send it to a VLM, or query the RAG database.
5.  **Action**: If physical movement is required, the agent sends commands to the ROS 2 controllers (`nav2` or `moveit2`).
6.  **Feedback**: The robot executes the action in O3DE, and the status is reported back to the HMI.

## 5. Where to Start

- **To Run the Demo**: Follow the [Quickstart Guide](./quickstart.md).
- **To Change Models**: Edit `config.toml` in the root directory.
- **To Modify Agent Behavior**: Explore `rai_app/agents/` to adjust how agents reason or interact.
- **To Customize the Robot**: Check `ros2_ws/src/robotec_kairos_ur10/` for robot parameters.
