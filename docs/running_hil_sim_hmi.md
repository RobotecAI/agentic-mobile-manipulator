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

```shell
pixi run serve-llm        # GPT-OSS-20B       → port 8080
pixi run serve-vlm        # LFM2-VL-3B        → port 8081
pixi run serve-embedding  # Qwen3-Embedding   → port 8082
pixi run serve-reranker   # Qwen3-Reranker    → port 8083
```

Models default to `$DEMO_ROOT/models/<filename>`. Override with env vars if your models are elsewhere:

```shell
LLM_MODEL=/path/to/model.gguf pixi run serve-llm
VLM_MODEL=/path/to/vlm.gguf VLM_MMPROJ=/path/to/mmproj.gguf pixi run serve-vlm
```

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
pixi run serve-embedding
pixi run serve-reranker
```
