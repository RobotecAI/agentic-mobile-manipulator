# RAI Agent

## Setup

1. Follow the basic setup instructions [here](../docs/setup.md).
2. Install the Python package:

```bash
cd ${DEMO_ROOT}
uv pip install -e .
```

## Run Agents

3. Launch the simulation.
4. Spawn objects in the simulation using the script:

```bash
uv run scripts/populate_scene.py
```

5. Run the nav2 agent:

```bash
source ros2_ws/install/setup.bash
uv run python rai_app/nav2_agent.py
```

6. Run the moveit agent:

```bash
source ros2_ws/install/setup.bash
uv run python rai_app/moveit2_agent.py
```

7. Run the agent:

```bash
source ros2_ws/install/setup.bash
uv run python rai_app/agent.py --task "Move all boxes from table t3 to the J01 rack. Then move the box from table t4 to rack j02" --agent_model "" --agent_vendor openai --agent_base_url http://127.0.0.1:8080/v1 --robot-namespace "" --recursion-limit 150
```

> [!TIP]
> If the inference engine is different from llama.cpp, adjust the agent_model and agent_vendor parameters accordingly.

8. For debugging, Langfuse is recommended. You can set it up locally at https://langfuse.com/self-hosting/deployment/docker-compose or use the cloud version at https://cloud.langfuse.com/.

The following ROS 2 topics should be available:

```bash
/agent/current_step
/agent/past_steps
```

These topics will inform you about the agent's current actions and completed tasks.
