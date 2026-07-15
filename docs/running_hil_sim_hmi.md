# Running a Demo on HIL, Simulation, and HMI

All commands use `pixi run` — the ROS 2 workspace is sourced automatically.

## Simulation Machine

### O3DE

```shell
pixi run sim
```

## HIL Machine

### ROS 2

```shell
pixi run stack
```

### Inference

Endpoints (model, backend, port, weights) are declared once in `config.toml`
under `[endpoints.*]`. Launch them all from that SSOT, or one at a time by name:

```shell
pixi run -e hil inference        # all local endpoints (tmux grid)

pixi run -e hil serve-llm        # endpoints.main_llm   → port 8080
pixi run -e hil serve-vlm-safety       # endpoints.vlm_safety     → port 8081 (NPU)
pixi run -e hil serve-vlm-inspection   # endpoints.vlm_inspection → port 8084 (GPU)
pixi run -e hil serve-embedding  # endpoints.embeddings → port 8082
pixi run -e hil serve-reranker   # endpoints.reranker   → port 8083
```

To use different weights, backend, or ports, edit the endpoint in `config.toml`
(`model_path`, `backend`, `port`, …). Preview without launching:
`pixi run -e hil inference --print`.

### Agents

```shell
pixi run agents
```

### Agent Orchestrator

```shell
pixi run orchestrator-agent
```

## HMI Machine

```shell
pixi run hmi
```

---

## Individual Agents

Use these when you want to run an agent separately instead of `pixi run agents`:

```shell
pixi run nav2-agent
pixi run moveit2-agent
pixi run scene-agent
pixi run inspection-agent
pixi run safety-agent
```

## Safety Embeddings and Reranker (optional)

These are only required when running the safety agent with RAG. See `docs/safety_agent_with_rag.md`.

```shell
pixi run -e hil serve-embedding
pixi run -e hil serve-reranker
```
