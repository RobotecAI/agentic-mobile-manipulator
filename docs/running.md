# Running the Demo

## O3DE

To run the O3DE, run the following command:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
${DEMO_ROOT}/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher
```

## ROS 2

To run the ROS 2 stack and control agents, execute:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
./scripts/run_ros2_stack.sh
```

## HMI

To run the HMI, execute:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch mobile_manipulator_hmi hmi_launch.py
```

# Inference

To run the inference, execute:

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -hf <model/s selected in `config.toml`>
```

e.g.

- GPT-OSS-20B

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m /path/to/downloaded/model/unsloth_gpt-oss-20b-GGUF_gpt-oss-20b-Q4_K_M.gguf --port 8080
```

- LFM2-VL-3B-GGUF

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m /path/to/downloaded/model/LFM2-VL-3B_public/LFM2-VL-3B-Q8_0.gguf --mmproj /path/to/downloaded/model/mmproj-LFM2-VL-3B-Q8_0.gguf --port 8081
```

- Qwen3-Embedding-0.6b

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m /path/to/downloaded/model/Qwen3-Embedding-0.6b_Q8_0.gguf --embedding --pooling last -c 4096 -b 2048 -ub 2048 --port 8082
```

- Qwen3-Reranker-0.6B

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m /path/to/downloaded/model/Qwen3-Reranker-0.6B.gguf --embedding --pooling rank -c 4096  -b 2048 -ub 2048 --port 8083
```

## Agent

For instructions, see: [Agent setup and inference](../rai_app/README.md)

## Local Runtime Components

These commands run the same components locally that are defined in `docker/compose.yaml`.
Each command assumes you have sourced your ROS 2 environment:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

### Configuration Files

- Local inference (default): `${DEMO_ROOT}/config.toml`

### Individual ROS 2 Components

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

### Agent Orchestrator

```shell
uv run python rai_app/agents/agent_orchestrator.py
```

### Safety Embeddings and Reranker (optional)

These services are only required if you run the safety agent with RAG. See `docs/safety_agent_with_rag.md`.

```shell
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m <embeddings_model.gguf> --embedding --pooling last --port 8082 --host 0.0.0.0
${DEMO_ROOT}/inference/llama.cpp/build/bin/llama-server -m <reranker_model.gguf> --embedding --pooling rank -fa on --port 8083 --host 0.0.0.0
```
