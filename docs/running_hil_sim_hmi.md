# Running a Demo on HIL, Simulation, and HMI

## Simulation

### O3DE

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
${DEMO_ROOT}/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher
```

## HIL

### ROS 2

To run the ROS 2 stack and control agents, execute:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
./scripts/run_ros2_stack.sh
```

### GenAI Inference

To run the GenAI inference, use:

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -hf unsloth/Qwen3-14B-GGUF
```

> [!TIP]
> This step can be skipped if an OpenAI-compatible endpoint is available.

### Agent

For instructions, see: [Agent setup and inference](../rai_app/README.md)

## HMI

### Running the GUI

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch mobile_manipulator_hmi hmi_launch.py
```
