# Setup HIL Environment

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy, provided by pixi via RoboStack (no separate ROS 2 install needed)
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

This runs, in order:

| Step | pixi task         | What it does                                                     |
| ---- | ----------------- | --------------------------------------------------------------- |
| 1    | `clone-ros2-ws`   | `vcs import` clones the ROS 2 workspace repositories            |
| 2    | `init-submodules` | Check out the pinned llama.cpp and FastFlowLM submodules        |
| 3    | `build-ros2`      | `colcon build` (dependencies come from conda/RoboStack, no rosdep) |
| 4    | `sync`            | `uv sync` installs the Python dependencies                      |
| 5    | `build-llama`     | Build llama.cpp with the Vulkan backend                         |

---

## Rebuilding llama.cpp

`pixi run -e hil setup` already builds llama.cpp with the Vulkan backend as its last step, so you normally don't run anything here. Use this section only to install the Vulkan SDK by hand or to rebuild llama.cpp on its own.

### Vulkan SDK

The llama.cpp build uses the Vulkan backend. Install the Vulkan SDK: [link](https://vulkan.lunarg.com/doc/sdk/1.4.321.1/linux/getting_started.html)

Verify it:

```shell
vulkaninfo
```

### Build llama.cpp on its own

```shell
pixi run -e hil build-llama
```

This checks out the llama.cpp submodule if needed and builds it with the Vulkan backend.

### Download Models

For every model configured in `config.toml`, download the GGUF file and place it in `$DEMO_ROOT/models/`.
See [Download Models](setup_single_machine.md#download-models) for links.
