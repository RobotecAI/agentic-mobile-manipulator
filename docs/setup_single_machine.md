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
```

#### Set the Root Directory of the Project

Set the root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding the following lines to your `.bashrc` or `.zshrc` file:

```shell
export DEMO_ROOT=/home/${USER}/agentic-mobile-manipulator
export O3DE_ROOT=${DEMO_ROOT}/engine/o3de
```

#### Install Base Dependencies

```bash
sudo apt update
sudo apt install git git-lfs ninja-build
```

#### Clone Repositories

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/engine.repos
vcs import --input ${DEMO_ROOT}/gems.repos
vcs import --input ${DEMO_ROOT}/ros2_ws.repos
```

### Setup O3DE

Install [packages required to build O3DE:](https://www.docs.o3de.org/docs/welcome-guide/requirements/#linux)

```shell
sudo apt install cmake libstdc++-12-dev clang libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev mesa-common-dev libunwind-dev libzstd-dev tix
```

Register the O3DE engine:

```shell
cd ${O3DE_ROOT}
git lfs install
git lfs pull
python/get_python.sh
${O3DE_ROOT}/scripts/o3de.sh register --this-engine
```

#### Setup o3de-extras

```shell
cd ${DEMO_ROOT}/gems
git lfs install
git lfs pull
```

### Setup ROS 2

#### Build the ROS 2 Workspace

```shell
cd ${DEMO_ROOT}/ros2_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```

Source the installation in your `.bashrc` or `.zshrc` file:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

### Build O3DE Editor and GameLauncher

```shell
cd ${DEMO_ROOT}/sim
cmake -B build/linux -G "Ninja Multi-Config" \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=ON \
    -DCMAKE_LINKER_TYPE=MOLD
cmake --build build/linux --config profile --target MobileManipulatorDemo Editor MobileManipulatorDemo.Assets MobileManipulatorDemo.GameLauncher
```

### Setup Python Environment

1. Install uv

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies

```shell
uv sync
```

### Setting Up llama.cpp (local inference)

> [!TIP]
> For the demo presented at ROSCon 2025, the Vulkan backend was used. For more information, see the [llama.cpp documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/inference.repos
```

```shell
cd ${DEMO_ROOT}/inference/llama.cpp

cmake -B build -DGGML_VULKAN=1
cmake --build build --config Release
```

### Download Models

For every configured model in `config.toml`, download the appropriate GGUF file and run it via `llama-server`.

For the default setup, download the following models:

- [GPT-OSS-20B](https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-Q4_K_M.gguf?download=true)
- [LFM2-VL-3B-GGUF](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/LFM2-VL-3B-Q8_0.gguf?download=true) along with [mmproj](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/mmproj-LFM2-VL-3B-Q8_0.gguf?download=true)
- [Qwen3-Embedding-0.6b](https://robotecai-my.sharepoint.com/:u:/g/personal/bartlomiej_boczek_robotec_ai/IQB7tkMkmi34Q6xtTB89N1LxAfod0sMpGT4uTffjo6iW7qc?e=6kLoTi)
- [Qwen3-Reranker-0.6B](https://robotecai-my.sharepoint.com/:u:/g/personal/bartlomiej_boczek_robotec_ai/IQAgWOVPiyS8RZ1QUVVx6N9gAaOGGrvDnk7Qa0IpSbhlp_8?e=P0b1Ak)

## Developer Setup

### Conventional Commits

We use conventional commits to ensure that the commit messages are consistent and follow a specific format. Read more about conventional commits [here](https://www.conventionalcommits.org/en/v1.0.0/).

### Pre-commit

We use pre-commit to ensure that the code is formatted and linted before it is committed.

```bash
sudo apt install pre-commit
pre-commit install
```

# Next Steps

- [Running the demo](./running.md)
