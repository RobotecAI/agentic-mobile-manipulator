# Setup HIL Environment

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

Set the root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding the following line to your `.bashrc` or `.zshrc` file:

```shell
export DEMO_ROOT=/home/${USER}/agentic-mobile-manipulator/
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

### Setup Python Environment

1. Install uv

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies

```shell
uv sync
```

## Setting Up llama.cpp

llama.cpp is used as the default GenAI inference engine. Other inference engines can be used if they maintain compatibility with the OpenAI API.

### Prerequisites

Install Vulkan SDK: [link](https://vulkan.lunarg.com/doc/sdk/1.4.321.1/linux/getting_started.html)

Verify Vulkan SDK is installed:

```shell
vulkaninfo
```

### Build llama.cpp

> [!TIP]
> In this example, Vulkan is used as the backend. Choose the appropriate backend based on your setup. For more information, see the [llama.cpp documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/inference.repos
```

```shell
cd ${DEMO_ROOT}/inference/llama.cpp

cmake -B build -DGGML_VULKAN=1
cmake --build build --config Release
```

### Download Model

For every configured model in `config.toml`, download and run the model using the following command:

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-cli -hf <model/s selected in `config.toml`>
```
