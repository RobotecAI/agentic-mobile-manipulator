# Running the Demo

## Run all at once

```shell
pixi run -e local demo
```

## Run separately

### O3DE

```shell
pixi run sim
```

### ROS 2

```shell
pixi run ros2
```

### HMI

```shell
pixi run hmi
```

### Local inference (llama.cpp)

Models default to `$DEMO_ROOT/models/<filename>`. Override with env vars if your models are elsewhere.

```shell
# GPT-OSS-20B — port 8080
pixi run -e local serve-llm

# LFM2-VL-3B — port 8081
pixi run -e local serve-vlm

# Qwen3-Embedding-0.6b — port 8082
pixi run -e local serve-embedding

# Qwen3-Reranker-0.6B — port 8083
pixi run -e local serve-reranker
```

To use a custom path:

```shell
LLM_MODEL=/path/to/gpt-oss-20b-Q4_K_M.gguf pixi run -e local serve-llm
VLM_MODEL=/path/to/LFM2-VL-3B-Q8_0.gguf VLM_MMPROJ=/path/to/mmproj.gguf pixi run -e local serve-vlm
EMBEDDING_MODEL=/path/to/embedding.gguf pixi run -e local serve-embedding
RERANKER_MODEL=/path/to/reranker.gguf pixi run -e local serve-reranker
```

### Agent Orchestrator

```shell
pixi run orchestrator
```
