# Setup HIL Environment

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Real-Time-Kernel-Tuning-Guide.html)
- Python: 3.12

## Building the Project

### Prerequisites

#### Clone the Repository

```shell
git clone https://github.com/RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

#### Install System Dependencies

```bash
sudo apt update
sudo apt install git git-lfs python3-vcstool
```

> [!NOTE]
> ROS 2 Jazzy with dev tools (including `colcon`, `rosdep`) must also be installed.
> See the [ROS 2 installation guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional).

#### Install pixi

[pixi](https://pixi.sh) orchestrates all build steps and sets environment variables automatically.

```shell
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your shell or run `source ~/.bashrc` after installation.

---

### Build

```shell
pixi run -e hil setup
```

This runs:

| Step | pixi task       | What it does                            |
| ---- | --------------- | --------------------------------------- |
| 1    | `clone-ros2-ws` | `vcs import` for ROS 2 workspace        |
| 2    | `rosdep-update` | `rosdep update` — refresh package index |
| 3    | `build-ros2`    | `rosdep install` + `colcon build`       |
| 4    | `sync`          | `uv sync` — install Python dependencies |

---

## Setting Up llama.cpp (optional)

llama.cpp is used as the default local GenAI inference engine. Skip this section if using a cloud API.

### Prerequisites

Install Vulkan SDK: [link](https://vulkan.lunarg.com/doc/sdk/1.4.321.1/linux/getting_started.html)

Verify Vulkan SDK is installed:

```shell
vulkaninfo
```

### Build llama.cpp

```shell
pixi run -e hil-local build-llama
```

This clones llama.cpp and builds it with Vulkan backend.

Or, to run the full HIL setup including llama.cpp in one command:

```shell
pixi run -e hil-local setup
```

### Download Models

For every model configured in `config.toml`, download the GGUF file and place it in `$DEMO_ROOT/models/`.
See [Download Models](setup_single_machine.md#download-models) for links.
