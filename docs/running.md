# Running the Demo

All commands use `pixi run` — the ROS 2 workspace is sourced automatically via `pixi_activate.sh`.

Run `pixi task list` to see all available commands.

## O3DE

```shell
pixi run sim
```

## ROS 2

```shell
pixi run ros2
```

## HMI

```shell
pixi run hmi
```

# Inference

## Local (llama.cpp)

Models default to `$DEMO_ROOT/models/<filename>`. Override with env vars if your models are elsewhere.

```shell
# GPT-OSS-20B — port 8080
pixi run serve-llm

# LFM2-VL-3B — port 8081
pixi run serve-vlm

# Qwen3-Embedding-0.6b — port 8082
pixi run serve-embedding

# Qwen3-Reranker-0.6B — port 8083
pixi run serve-reranker
```

To use a custom path:

```shell
LLM_MODEL=/path/to/gpt-oss-20b-Q4_K_M.gguf pixi run serve-llm
VLM_MODEL=/path/to/LFM2-VL-3B-Q8_0.gguf VLM_MMPROJ=/path/to/mmproj.gguf pixi run serve-vlm
EMBEDDING_MODEL=/path/to/embedding.gguf pixi run serve-embedding
RERANKER_MODEL=/path/to/reranker.gguf pixi run serve-reranker
```

## Agent

For instructions, see: [Agent setup and inference](../rai_app/README.md)

## Local Runtime Components

### Agent Orchestrator

```shell
pixi run orchestrator
```

### Individual Components

Use these when you want to run components separately instead of `pixi run ros2`:

```shell
pixi run nav2-agent
pixi run moveit2-agent
pixi run scene-agent
pixi run inspection-agent
pixi run safety-agent
```

### Safety Embeddings and Reranker (optional)

These are only required when running the safety agent with RAG. See `docs/safety_agent_with_rag.md`.

```shell
EMBEDDING_MODEL=/path/to/embeddings.gguf pixi run serve-embedding
RERANKER_MODEL=/path/to/reranker.gguf pixi run serve-reranker
```
