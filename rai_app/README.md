# rai agent

## Setup

1. Follow the basic setup instructions
2. install python package:

```bash
cd ${DEMO_ROOT}
uv pip install -e .
```

## Run Agent

3. Launch the simulation
4. Spawn objects in the simulation, you can do it with script:

```bash
 uv run scripts/populate_scene.py
```

5. Run agent

```bash
source ros2_ws/install/setup.bash
uv run python rai_app/agent.py --task "Move box from table t1, Slot6 to rack J01 RackSlot6" --agent_model gpt-4o --agent_vendor openai --vlm_model gpt-4o --vlm_vendor openai --robot-namespace "" --recurssion-limit 150
```

7. For debugging agent langfuse is recommended. You can set it up locally -> https://langfuse.com/self-hosting/deployment/docker-compose
   or use cloud https://cloud.langfuse.com/

8. Ros topics should be available:

```bash
/agent/current_step
/agent/past_steps
```

They will tell you what agent is currently doing and what has been done.
