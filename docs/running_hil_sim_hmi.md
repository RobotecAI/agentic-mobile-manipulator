# Running a demo on HIL, Simulation, and HMI

## Simulation

### O3DE

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
${DEMO_ROOT}/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher
```

## HIL

### ROS 2

Run the ROS 2 stack:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch robotec_kairos_ur10 robotec_launch.py
```

### GenAI inference

Run the GenAI inference:

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -hf unsloth/Qwen3-14B-GGUF
```

> [!TIP]
> This step can be skipped, provided an OpenAI compatible endpoint is available.

### Agent

Instructions: [Agent setup and inference](../rai_app/README.md)

## HMI

### Running the GUI

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 run mobile_manipulator_hmi MobileManipulatorHMI
```
