# Running the Demo

## What to expect

![Demo Windows](demo_windows.jpg)

1. **Simulation Window**: the O3DE warehouse environment. Use _Control → Simulation Scenarios_ to spawn objects, and _Control → On Demand predefined tasks_ to run tasks — or publish your own to the `/user_tasks` topic.
2. **HMI**: a window showing the Human-Machine Interface.
3. **Agents**: the autonomous agents run in the background, driving the robot.

See how to operate the demo [Operating](operating.md)

## Run all at once

```shell
pixi run -e single-pc-gpu-and-npu demo
```

> [!TIP]
> If you have a system-installed ROS 2, pass the `--clean-env` flag to `pixi run`, or use Docker for clean isolation. Otherwise the demo may fail to start due to an API/ABI mismatch.

## tmux sessions

Each component runs in its own detached tmux session named
`agentic-mobile-manipulator-<component>` (`-sim`, `-stack`, `-llm-servers`,
`-agents`, `-hmi`). `pixi run demo` starts all of them in the background and prints
the attach commands. Running a single task such as `pixi run sim` attaches you to
its session directly.

Attach to a session from another terminal (swap the suffix for any component):

```shell
tmux attach -t agentic-mobile-manipulator-sim
```

Inside tmux, `Ctrl-b s` lists and switches sessions and `Ctrl-b d` detaches. Stop
every session with:

```shell
pixi run kill
```

To run a component in the foreground instead (no tmux), use its `-fg` variant:
`pixi run sim-fg`, `pixi run stack-fg`, or `pixi run hmi-fg`.

## Run separately

### O3DE

```shell
pixi run sim
```

### ROS 2

```shell
pixi run stack
```

### HMI

```shell
pixi run hmi
```

### Local inference

Every inference endpoint is declared once in [`config.toml`](../config.toml) under
`[endpoints.*]` (model, backend, port, weights). `pixi run inference` reads that
SSOT and launches each server on its backend — `gpu`/`cpu` via llama.cpp, `npu`
via FastFlowLM — in a tmux grid:

```shell
pixi run -e single-pc-gpu-and-npu inference        # launch all local endpoints (tmux grid)
pixi run -e single-pc-gpu-and-npu smoke-test       # health-check them
```

To start a single endpoint (e.g. for debugging), launch it by its endpoint name:

```shell
pixi run -e single-pc-gpu-and-npu serve-llm        # endpoints.main_llm   → port 8080
pixi run -e single-pc-gpu-and-npu serve-vlm-safety       # endpoints.vlm_safety     → port 8081 (NPU)
pixi run -e single-pc-gpu-and-npu serve-vlm-inspection   # endpoints.vlm_inspection → port 8084 (GPU)
pixi run -e single-pc-gpu-and-npu serve-embedding  # endpoints.embeddings → port 8082
pixi run -e single-pc-gpu-and-npu serve-reranker   # endpoints.reranker   → port 8083
```

To change a weight path, backend, or port, edit the endpoint in `config.toml`
(e.g. set `model_path`, or flip the VLM `backend` between `gpu` and `npu`).
Preview the resolved launch commands without starting anything:

```shell
pixi run -e single-pc-gpu-and-npu inference --print
```

### Agents

```shell
pixi run agents
```

### Agent Orchestrator

```shell
pixi run orchestrator-agent
```
