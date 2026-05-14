# Setup

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the Project

### Prerequisites

#### Clone the Repository

```shell
cd /home/${USER}
git clone git@github.com:RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

#### Install System Dependencies

These packages must be installed via `apt` before using pixi:

```bash
sudo apt update
sudo apt install git git-lfs python3-vcstool ninja-build \
    cmake libstdc++-12-dev clang \
    libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 \
    libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev \
    libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev \
    mesa-common-dev libunwind-dev libzstd-dev tix
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

### Build Everything

```shell
pixi run setup
```

This single command runs the full build pipeline in the correct order:

| Step | pixi task       | What it does                                          |
| ---- | --------------- | ----------------------------------------------------- |
| 1    | `clone`         | `vcs import` for engine, gems, and ROS 2 workspace    |
| 2    | `setup-o3de`    | git-lfs pull + O3DE engine registration               |
| 3    | `register-gems` | Register all O3DE gems and the simulation project     |
| 4    | `build-ros2`    | `rosdep install` + `colcon build`                     |
| 5    | `build-o3de`    | CMake configure + Ninja build (Editor + GameLauncher) |
| 6    | `sync`          | `uv sync` — install Python dependencies               |

> [!NOTE] > `build-o3de` takes 30–60 minutes on first run.

#### Local Inference (optional)

If you want to run models locally via llama.cpp instead of cloud APIs:

```shell
pixi run clone-inference
pixi run build-llama
```

Then [download the required models](#download-models).

---

### Running the Demo

`pixi run` replaces all manual `source` calls — the ROS 2 environment is sourced automatically.

```shell
# In separate terminals:
pixi run sim          # O3DE simulation
pixi run ros2         # Full ROS 2 stack
pixi run orchestrator # Agent orchestrator
```

For the HMI:

```shell
pixi run hmi
```

Individual agents (for debugging):

```shell
pixi run nav2-agent
pixi run moveit2-agent
pixi run scene-agent
pixi run inspection-agent
pixi run safety-agent
```

Local inference servers:

```shell
# Models default to $DEMO_ROOT/models/<filename>.
# Override with env vars, e.g.: LLM_MODEL=/path/to/model.gguf pixi run serve-llm
pixi run serve-llm        # GPT-OSS-20B  → port 8080
pixi run serve-vlm        # LFM2-VL-3B   → port 8081
pixi run serve-embedding  # Qwen3-Embedding-0.6b → port 8082
pixi run serve-reranker   # Qwen3-Reranker-0.6B  → port 8083
```

Run `pixi task list` to see all available commands.

---

### Download Models

For every model configured in `config.toml`, download the GGUF file and place it in `$DEMO_ROOT/models/`:

- [GPT-OSS-20B](https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-Q4_K_M.gguf?download=true)
- [LFM2-VL-3B-GGUF](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/LFM2-VL-3B-Q8_0.gguf?download=true) + [mmproj](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/mmproj-LFM2-VL-3B-Q8_0.gguf?download=true)
- [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf?download=true)
- [Qwen3-Reranker-0.6B](https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/resolve/main/qwen3-reranker-0.6b-q8_0.gguf?download=true)

---

## Developer Setup

### Conventional Commits

We use conventional commits to ensure that the commit messages are consistent and follow a specific format. Read more about conventional commits [here](https://www.conventionalcommits.org/en/v1.0.0/).

### Pre-commit

```bash
pixi run pre-commit-install
```

To run hooks manually:

```bash
pixi run lint
```

# Next Steps

- [Running the demo](./running.md)
