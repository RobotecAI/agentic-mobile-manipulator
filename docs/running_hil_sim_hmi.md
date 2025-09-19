# Running a demo on HIL, Simulation, and HMI

## Simulation

### O3DE

To run the O3DE, run the following command and choose `DemoLevel.prefab` from the level menu.

1. Open the editor

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

### Agent

You can run the agent as follows:

> [!NOTE]
>
> - By default, the agent uses the **OpenAI GPT-5** model. An `OPENAI_API_KEY` environment variable must be set.
> - To use another model, provide `--model-name` for the model identifier and `--base-url` for an OpenAI-compatible endpoint.
> - If no arguments are given, the agent runs a default task: navigating to one of the predefined points of model's choosing, capturing an image from the camera, and describing it.

```shell
cd ${DEMO_ROOT}
uv run python rai_app/agent.py [--prompt ...] [--model-name gpt-5] [--base-url ...]
```

## HMI

### Running the GUI

```shell
${DEMO_ROOT}/MobileManipulatorHMI/build/linux/MobileManipulatorHMI
```
