# Setup

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy, provided by pixi via RoboStack (no separate ROS 2 install needed)
- Python: 3.12

## Building the Project

### Prerequisites

#### Clone the Repository

```shell
git clone https://github.com/RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

#### Install System Dependencies

These packages must be installed via `apt` before using pixi:

```bash
sudo apt update
sudo apt install git git-lfs python3-vcstool ninja-build \
    cmake libstdc++-12-dev clang \
    libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 \
    libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev \
    libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev \
    mesa-common-dev libunwind-dev libzstd-dev tix
```

#### Install pixi

[pixi](https://pixi.sh) orchestrates all build steps and sets environment variables automatically.

```shell
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your shell or run `source ~/.bashrc` after installation.

---

### Build Everything

```shell
pixi run -e single-pc-gpu-and-npu setup
```

This single command runs the full build pipeline in the correct order:

| Step | pixi task          | What it does                                                   |
| ---- | ------------------ | -------------------------------------------------------------- |
| 1    | `clone`            | `vcs import` + `git lfs pull` for gems and ROS 2 ws            |
| 2    | `install-o3de`     | Install the O3DE engine                                        |
| 3    | `fetch-gems`       | Clone o3de-extras locally, validate all gem paths              |
| 4    | `build-ros2`       | `colcon build` (deps provided by RoboStack)                    |
| 5    | `build-sim`        | CMake configure + Ninja build (GameLauncher)                   |
| 6    | `sync`             | `uv sync` installs the Python dependencies                     |
| 7    | `build-llama`      | Build llama.cpp with the Vulkan backend (GPU)                  |
| 8    | `build-fastflowlm` | Build FastFlowLM for the AMD Ryzen AI NPU backend              |
| 9    | `find-runnables`   | List the built runnables (GameLauncher, llama.cpp, FastFlowLM) |

> Prefer a GPU-only machine (no AMD Ryzen AI NPU)? Use `pixi run -e single-pc-gpu setup`
> instead — it skips step 8. You must also set `[endpoints.vlm_safety] backend = "gpu"`
> in `config.toml`; otherwise inference routes that endpoint to the NPU.

#### Local Inference

Setup already checks out the inference submodules and builds both backends —
llama.cpp (Vulkan, GPU) and FastFlowLM (NPU) — as part of the pipeline above. To
serve models locally you still need to download the weights:

```shell
pixi run -e single-pc-gpu-and-npu download-models # downloads every weight referenced in config.toml (gguf via wget, NPU tags via `flm pull`); or grab them manually below
```

`config.toml` is the single source of truth for inference: each `[endpoints.*]`
table fixes a model's backend, port, and weights, and the agents reference those
endpoints by name. `pixi run inference` launches them all. See
[Running the demo](running.md#local-inference).

##### NPU backend (AMD Ryzen™ AI)

The `single-pc-gpu-and-npu` setup above builds FastFlowLM (step 8), so NPU
endpoints are served without extra configuration. The [RobotecAI/FastFlowLM](https://github.com/RobotecAI/FastFlowLM)
fork (pinned as a submodule) includes GBNF grammar-constrained sampling, so the
NPU path can produce the structured/JSON output the agents rely on. Which
endpoints run on the NPU is driven by `backend = "npu"` entries in `config.toml`
— the NPU VLM endpoint serves a FastFlowLM vision tag (default `gemma3:4b`); see
`[endpoints.vlm_safety]`.

Building FastFlowLM only needs the XRT/amdxdna dev headers, but **serving** on
the NPU requires an AMD Ryzen AI processor with the `amdxdna` driver loaded. On an
AMD machine without the NPU, use the GPU-only `single-pc-gpu` setup and switch
`[endpoints.vlm_safety]` to `backend = "gpu"` in `config.toml`, so every endpoint
runs on llama.cpp.

---

### Download Models

For every GGUF-backed model in `config.toml`, download the file and place it in `$DEMO_ROOT/models/`:

- [GPT-OSS-20B](https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-Q4_K_M.gguf?download=true)
- [LFM2-VL-3B-GGUF](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/LFM2-VL-3B-Q8_0.gguf?download=true) + [mmproj](https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF/resolve/main/mmproj-LFM2-VL-3B-Q8_0.gguf?download=true)
- [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf?download=true)
- [Qwen3-Reranker-0.6B](https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/resolve/main/qwen3-reranker-0.6b-q8_0.gguf?download=true)

The NPU `vlm_safety` model (`gemma3:4b`) has no GGUF; `flm pull` downloads it for you.

---

## Verify your installation

Once the build is done and the weights are downloaded, run one command to exercise
the whole stack end to end:

```shell
pixi run -e single-pc-gpu-and-npu demo-trace
```

This brings up the full demo (sim, stack, inference, agents, HMI), populates the
scene, sends one task to the orchestrator (ship one CPU), waits for it to finish,
saves the agent trace, and shuts everything down. A successful run ends with:

```
  ● Task complete (marker).

=== Trace saved ===
  runs/<timestamp>
    log.txt         human-readable conversation (orchestrator + subagents)
    trace.jsonl     one JSON record per event
    agents_pane.log raw agents tmux output
    manifest.txt    task + timestamps
```

Open `runs/<timestamp>/log.txt` to read the orchestrator and subagent conversation
for the task.

Environment knobs:

- `TASK`: the task string sent to the orchestrator (default: ship one CPU)
- `MAX_WAIT`: hard cap in seconds on task execution (default: 900)
- `IDLE`: treat this many seconds of trace inactivity as done (default: 180)
- `SKIP_SCENE=1`: skip scene population
- `TRACE_DIR`: output directory (default: `runs/<timestamp>`)

On a GPU-only box, use `-e single-pc-gpu` and set
`[endpoints.vlm_safety] backend = "gpu"` in `config.toml` first (see above).

The conversation trace is written on any agent run (default-on, to `runs/<timestamp>/`);
`demo-trace` just automates a single task plus teardown. Set `AMM_TRACE=0` to
disable it.

### Richer traces with Langfuse (optional)

The orchestrator is already instrumented with a Langfuse callback. Point it at a
Langfuse instance (self-hosted or cloud) to get a full browsable trace, including
nested subagent spans and token usage, alongside the local `runs/` files:

```shell
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=http://localhost:3000   # your Langfuse server
```

Without these keys the callback stays inactive and only the local `runs/` trace is
written.

---

## Developer Setup

### Conventional Commits

We use conventional commits to ensure that the commit messages are consistent and follow a specific format. Read more about conventional commits [here](https://www.conventionalcommits.org/en/v1.0.0/).

### Pre-commit

```bash
pixi run -e dev pre-commit-install
```

To run hooks manually:

```bash
pixi run -e dev lint
```

# Next Steps

- [Running the demo](./running.md)
