# Quickstart Guide

This guide will help you get the **Mobile Manipulator Demo** up and running quickly using Docker Compose.

## Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) installed.
- **For AMD GPUs**: [ROCm Docker prerequisites](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html#prerequisites).
- **For Nvidia GPUs**: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed and configured.

## 1. Prepare the environment

### 1.1 Clone the repository

```bash
git clone https://github.com/RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

### 1.2 Configure the LLM/VLM

config.toml file is used to configure the LLM/VLM models. By default, the demo uses OpenAI.
If you want to use other models, modify the config.toml accordingly.

## 2. Run the demo

### 2.1 Allow local connections to your X server

Before launching the containers, you need to allow local connections to your X server so the GUI applications (O3DE simulation and HMI) can display on your screen.

Run the following command in your terminal:

```bash
xhost +local:docker
```

### 2.2 Run the demo

### Option 1: AMD GPU

If you have an AMD GPU, use the `amd` compose file:

```bash
docker compose -f docker/compose.amd.yaml up
```

### Option 2: Nvidia GPU

If you have an Nvidia GPU, use the `nvidia` compose file:

```bash
docker compose -f docker/compose.nvidia.yaml up
```

## What to Expect

![Demo Windows](demo_windows.jpg)

1.  **Simulation Window**: The O3DE simulation window will appear, showing the warehouse environment. Use "Control -> Simulation Scenarios" to spawn objects in the warehouse. Use "Control -> On demand predefined tasks" to run predefined tasks. Alternatively, publish your own tasks to the `/user_tasks` topic.
2.  **HMI**: A separate window or terminal output indicating the HMI is running will appear. Spawn
3.  **Agents**: The autonomous agents will start in the background.

## Troubleshooting

- **O3DE Doesn't start**: Ensure you have the correct GPU drivers and container toolkit installed. Run `docker compose -f docker/compose.***.yaml up sim` to see the logs.
- **Display Issues**: If windows don't appear, ensure you ran `xhost +local:docker` and that your `DISPLAY` environment variable is set correctly (`echo $DISPLAY`).
- **GPU Access**: If the simulation runs slowly or crashes, check your GPU drivers and container toolkit installation.
- **AMD GPU Access**: Ensure you have passed the correct devices. For more details on running ROCm Docker containers, see the [official AMD documentation](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html).
