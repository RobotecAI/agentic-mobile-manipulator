# Quickstart: Docker Compose

Run the full **Mobile Manipulator Demo** (simulation, ROS 2 stack, local inference, agents, and HMI) in a single container, with every model served locally.

## Pick a variant

|                | GPU + NPU (default)                                         | GPU only                           |
| -------------- | ----------------------------------------------------------- | ---------------------------------- |
| Hardware       | AMD GPU + AMD Ryzen™ AI NPU (e.g. Ryzen AI Max, Strix Halo) | Any supported AMD GPU              |
| Safety VLM     | `gemma3:4b` on the NPU (FastFlowLM)                         | LFM2-VL on the GPU (llama.cpp)     |
| Image          | Built locally with `WITH_NPU=1`                             | Prebuilt (`pull`) or built locally |
| Mounted config | `config.toml`                                               | `gpu_config.toml`                  |

The published image is GPU only: it does not ship FastFlowLM. A Ryzen AI machine can still run it, using only the GPU.

Set the variant once in your shell; every command below uses it:

```bash
# GPU + NPU (default)
export WITH_NPU=1 AMM_CONFIG=../config.toml

# GPU only
export WITH_NPU=0 AMM_CONFIG=../gpu_config.toml
```

`WITH_NPU` selects what the image is built with, `AMM_CONFIG` which config the container runs. Without `AMM_CONFIG`, compose mounts `gpu_config.toml` and the NPU stays unused even in an NPU image.

## Prerequisites

- **AMD GPU** (ROCm/Vulkan).
- [Docker Engine](https://docs.docker.com/engine/install/) + [ROCm Docker prerequisites](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html#prerequisites).
- A running X server (the O3DE simulation and HMI open windows on your display).
- **Disk & network**: ~60 GB free for the image (the prebuilt image is a ~18 GB compressed pull), plus ~27 GB under `models/` for the weights. On a slow connection the first pull + model download takes a while.
- **GPU + NPU only**: the host's `amdxdna` driver (`ls /dev/accel/accel0`) and NPU firmware 1.1 or newer. Ubuntu 24.04 ships 1.0.0.166; install the newer one as in [NPU prerequisites](setup_single_machine.md#npu-prerequisites-single-pc-gpu-and-npu-only) (only the firmware part: the XRT build packages are inside the image).
- **GPU only, on a host without an NPU**: remove the `/dev/accel/accel0` device and the `memlock` ulimit from `x-demo-runtime` in `docker/compose.yaml`; compose refuses to start with a missing device.

## 1. Clone the repository

```bash
git clone https://github.com/RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

## 2. Get the image

**GPU + NPU: build locally.**

```bash
docker compose -f docker/compose.yaml build
```

This builds three cacheable layers: `…-ros2` (RoboStack ROS 2 + workspace), `…-o3de` (O3DE SDK + simulation) and `…demo` (Python agents, llama.cpp and, with `WITH_NPU=1`, FastFlowLM). The O3DE layer is large; later rebuilds reuse the cached bases.

**GPU only: build the same way, or pull the prebuilt images.**

```bash
docker compose -f docker/compose.yaml pull
```

## 3. Download the model weights

Weights are **not** baked into the image. The mounted config (`$AMM_CONFIG`) says which models are fetched; download them once:

```bash
docker compose -f docker/compose.yaml run --rm --no-build --entrypoint "" demo pixi run download-models
```

This downloads the llama.cpp GGUFs into `models/` in parallel, one progress bar per file, and with GPU + NPU the NPU model via `flm pull` into the `flm-models` Docker volume (`docker volume rm docker_flm-models` removes it). Partial files resume and complete ones are skipped, so it's safe to re-run.

## 4. Run the demo

Allow local connections to your X server, then start the `demo` service:

```bash
xhost +local:root
docker compose -f docker/compose.yaml up --no-build demo
```

> [!IMPORTANT]
> Always pass `--no-build`, whether you built or pulled the image. Without it, `up` (and `run`) rebuild `ros2 → o3de → demo` first, and any repository change since your build (a commit, a `git pull`) turns that into a long rebuild.

## What to expect

![Demo windows: HMI, simulation and RViz](demo_windows.jpg)

1. **Simulation window**: the O3DE warehouse environment.
2. **HMI**: populate the scene on its **Simulation** page, then assign tasks there or on the **Mission** page, and follow the agents on the **Mission** and **Agents** pages.
3. **Agents**: the autonomous agents run in the background, driving the robot.

See how to operate the demo [Operating](operating.md)

## Verify the install (one-shot trace run)

Instead of the interactive `demo`, the `demo-trace` service runs the whole stack,
sends one task to the orchestrator, saves the agent conversation trace, and exits:

```bash
xhost +local:root
docker compose -f docker/compose.yaml run --rm --no-build demo-trace
```

The trace is written to `runs/<timestamp>/` on the host (bind-mounted from the
container; files are root-owned, `chown` if needed). Override the task with
`-e TASK="Do Housekeeping of rack J01"`. See
[Verify your installation](setup_single_machine.md#verify-your-installation) for
the full list of knobs and the Langfuse option.

## Inspecting a component

Each component runs in its own tmux session inside the container. Attach to one (e.g. the simulation) from the host:

```bash
docker exec -it $(docker ps -qf ancestor=robotecai/agentic-mobile-manipulator:latest) \
  tmux attach -t agentic-mobile-manipulator-sim
```

Swap the session for any of `-sim`, `-stack`, `-llm-servers`, `-agents`, `-hmi` (all prefixed `agentic-mobile-manipulator-`). Inside tmux, `Ctrl-b s` lists/switches sessions and `Ctrl-b d` detaches.

## Stopping

```bash
docker compose -f docker/compose.yaml down
```

## Cloud models

To run the agents on OpenAI-hosted models instead of local inference, mount the
cloud config (the compose mounts `$AMM_CONFIG` as the container's `config.toml` and
passes `OPENAI_API_KEY` into the container):

```bash
export AMM_CONFIG=../cloud_config.toml
export OPENAI_API_KEY=sk-...
```

Only the RAG embedding + reranker are still served locally, so step 3 downloads
just those two GGUFs. See
[Using cloud models](setup_single_machine.md#using-cloud-models-instead-low-vram-machines)
for details, including the required OpenAI model access.

## Troubleshooting

- **O3DE doesn't start / no windows appear**: ensure you ran `xhost +local:root` and that `DISPLAY` is set (`echo $DISPLAY`). Verify your AMD GPU drivers + ROCm container prerequisites are installed.
- **NPU errors / FastFlowLM fails to start**: confirm `/dev/accel/accel0` exists on the host, the NPU firmware is 1.1 or newer (on firmware 1.0 every request fails with `ERT_CMD_STATE_ABORT`), the image was built with `WITH_NPU=1`, you started with `AMM_CONFIG=../config.toml`, and the `memlock` ulimit and the device mapping are present in `docker/compose.yaml` (both are required for the NPU).
- **Inference health check fails**: make sure step 3 ran with the same `AMM_CONFIG` you run with, so `models/` (and, for the NPU, the `flm-models` volume) holds the weights the mounted config references.
- **GPU access / slow or crashing sim**: check your GPU drivers and the [ROCm Docker docs](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html).
