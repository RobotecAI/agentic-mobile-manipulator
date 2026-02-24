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

### Inference

To run the inference, execute:

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -hf <model/s selected in `config.toml`>
```

## HMI

### Running the GUI

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch mobile_manipulator_hmi hmi_launch.py
```

## Local Runtime Components

These commands run the same components locally that are defined in `docker/compose.yaml`.
Each command assumes you have sourced your ROS 2 environment:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

### Configuration Files

- Local inference (default): `${DEMO_ROOT}/config.toml`

## Individual ROS 2 Components

Use these commands when you want to run components separately instead of `./scripts/run_ros2_stack.sh`:

```shell
ros2 launch robotec_kairos_ur10 robotec_launch.py
ros2 run mobile_manipulator_hmi utilization_node
uv run python rai_app/agents/nav2_agent.py
uv run python rai_app/agents/moveit2_agent.py
uv run python rai_app/environment/scene_agent.py
ros2 run nav2_lifecycle_manager nav_lifecycle_node
uv run python rai_app/agents/inspection_agent.py
${DEMO_ROOT}/scripts/start_safety_agent.sh
```

Start the orchestrator:

For instructions, see: [Agent setup and inference](../rai_app/README.md)

## Safety Embeddings and Reranker (optional)

These services are only required if you run the safety agent with RAG. See `docs/safety_agent_with_rag.md`.

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m <embeddings_model.gguf> --embedding --pooling last --port 8082 --host 0.0.0.0
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m <reranker_model.gguf> --embedding --pooling rank -fa on --port 8083 --host 0.0.0.0
```
