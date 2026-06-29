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
pixi run ros2
```

### Inference

Endpoints (model, backend, port, weights) are declared once in `config.toml`
under `[endpoints.*]`. Launch them all from that SSOT, or one at a time by name:

```shell
pixi run -e hil-local inference        # all local endpoints (tmux grid)

pixi run -e hil-local serve-llm        # endpoints.main_llm   → port 8080
pixi run -e hil-local serve-vlm        # endpoints.vlm        → port 8081
pixi run -e hil-local serve-embedding  # endpoints.embeddings → port 8082
pixi run -e hil-local serve-reranker   # endpoints.reranker   → port 8083
```

To use different weights, backend, or ports, edit the endpoint in `config.toml`
(`model_path`, `backend`, `port`, …). Preview without launching:
`pixi run -e hil-local inference --print`.

### Agent Orchestrator

```shell
pixi run orchestrator
```

## HMI Machine

```shell
pixi run hmi
```

---

## Individual ROS 2 Components

Use these when you want to run components separately instead of `pixi run ros2`:

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
pixi run -e hil-local serve-embedding
pixi run -e hil-local serve-reranker
```
