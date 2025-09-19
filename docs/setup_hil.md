# Setup HIL Environment

The contents of this repository are compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the project

### Prerequisites

#### Clone the repository

```shell
cd /home/${USER}
git clone git@github.com:RobotecAI/golden-hiptage.git
```

#### Set root directory of the project

Set root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding following line to `.bashrc` or `.zshrc` file:

```shell
export DEMO_ROOT=/home/${USER}/golden-hiptage/
```

### Setup ROS 2

#### Build ROS 2 workspace

```shell
cd ${DEMO_ROOT}/ros2_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```

Source the installation to `.bashrc` or `.zshrc` file:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

### Setup python environment

1. Install uv

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies

```shell
uv sync
```

## Setting up llama.cpp

llama.cpp is used as the default GenAI inference engine. Other inference engines can be used if they maintain compatibility with OpenAI API.

### Prerequisites

Install Vulkan SDK: [link](https://vulkan.lunarg.com/doc/sdk/1.4.321.1/linux/getting_started.html)

Verify Vulkan SDK is installed:

```shell
vulkaninfo
```

### Build llama.cpp

> [!TIP]
> In this example, Vulkan is used as the backend. Choose the appropriate backend based on your setup. For more information see [llama.cpp documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/inference.repos
```

```shell
cd ${DEMO_ROOT}/inference/llama.cpp

cmake -B build -DGGML_VULKAN=1
cmake --build build --config Release
```

### Download model

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-cli -hf unsloth/Qwen3-14B-GGUF

```
