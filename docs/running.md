# Running the Demo

## Run all at once

```shell
pixi run -e single-pc demo
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

### Local inference

Every inference endpoint is declared once in [`config.toml`](../config.toml) under
`[endpoints.*]` (model, backend, port, weights). `pixi run inference` reads that
SSOT and launches each server on its backend — `gpu`/`cpu` via llama.cpp, `npu`
via FastFlowLM — in a tmux grid:

```shell
pixi run -e single-pc inference        # launch all local endpoints (tmux grid)
pixi run -e single-pc smoke-test       # health-check them
```

To start a single endpoint (e.g. for debugging), launch it by its endpoint name:

```shell
pixi run -e single-pc serve-llm        # endpoints.main_llm   → port 8080
pixi run -e single-pc serve-vlm-safety       # endpoints.vlm_safety     → port 8081 (NPU)
pixi run -e single-pc serve-vlm-inspection   # endpoints.vlm_inspection → port 8084 (GPU)
pixi run -e single-pc serve-embedding  # endpoints.embeddings → port 8082
pixi run -e single-pc serve-reranker   # endpoints.reranker   → port 8083
```

To change a weight path, backend, or port, edit the endpoint in `config.toml`
(e.g. set `model_path`, or flip the VLM `backend` between `gpu` and `npu`) — there
are no per-server env vars anymore. Preview the resolved launch commands without
starting anything:

```shell
pixi run -e single-pc inference --print
```

### Agent Orchestrator

```shell
pixi run orchestrator
```
