# Setup

> [!NOTE]
> This setup guide describes the configuration used for the original demo presented at ROSCon 2025.
> The demo was run on an AMD Ryzen™ AI mini PC with 128GB of total RAM, 64GB of which was allocated to the GPU.

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12
- OpenAI-compatible Endpoint for GenAI inference (llama.cpp)

## Setup Options

You can run the demo on either a single computer or across three separate machines.
Choose the guide that matches your setup.

### Single Machine Setup

Run everything on one computer

[Single-machine setup](./setup_single_machine.md)

### Three Machines

Setup resembling a real-world scenario:

- Simulation
- HiL (Hardware-in-the-Loop)
- HMI (Human–Machine Interface)

[Three-machine setup: HiL, Simulation, and HMI](./setup_hil_sim_hmi.md)
