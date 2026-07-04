# Quickstart: Docker Compose

Run the full **Mobile Manipulator Demo** — simulation, ROS 2 stack, local inference, agents, and HMI — in a single container, with all models served locally on an AMD GPU + AMD Ryzen™ AI NPU.

## Prerequisites

- **AMD GPU** (ROCm/Vulkan) **and AMD Ryzen™ AI NPU** for the default build.
- The host's **amdxdna** driver loaded: check with `ls /dev/accel/accel0`.
- [Docker Engine](https://docs.docker.com/engine/install/) + [ROCm Docker prerequisites](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html#prerequisites).
- A running X server (the O3DE simulation and HMI open windows on your display).
- ~60 GB free disk for the image, plus room under `models/` for the weights.

## 1. Clone the repository

```bash
git clone https://github.com/RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

## 2. Get the image: build _or_ pull

**Build locally:**

```bash
docker compose -f docker/compose.yaml build
```

This builds three cacheable layers — `…-ros2` (RoboStack ROS 2 + workspace) → `…-o3de` (O3DE SDK + simulation) → `…demo` (Python agents + llama.cpp + FastFlowLM). The O3DE layer is large; later rebuilds reuse the cached bases.

**Or pull the prebuilt images:**

```bash
docker compose -f docker/compose.yaml pull
```

If you pull, pass `--no-build` when starting the demo (see step 4).

## 3. Download the model weights

Weights are **not** baked into the image. They are downloaded into the repo's `models/` directory, bind-mounted at run time. `config.toml` is the single source of truth for which models are fetched. Pull them once into `models/` by running:

```bash
docker compose -f docker/compose.yaml run --rm --entrypoint "" demo pixi run download-models
```

This writes the llama.cpp GGUFs to `models/` and the NPU model to `models/flm/` (via `flm pull`). It only fetches what's missing, so it's safe to re-run.

## 4. Run the demo

Allow local connections to your X server, then start the `demo` service:

```bash
xhost +local:root
docker compose -f docker/compose.yaml up demo          # if you built (step 2)
docker compose -f docker/compose.yaml up --no-build demo   # if you pulled (step 2)
```

> [!IMPORTANT]
> The `docker compose up` command rebuilds any service that has a `build:` section, even when the image is already present locally. So after `pull`, a bare `up demo` ignores the pulled image and rebuilds `ros2 → o3de → demo`. Pass `--no-build` to run the pulled image as-is.

## What to expect

![Demo Windows](demo_windows.jpg)

1. **Simulation Window**: the O3DE warehouse environment. Use _Control → Simulation Scenarios_ to spawn objects, and _Control → On Demand predefined tasks_ to run tasks — or publish your own to the `/user_tasks` topic.
2. **HMI**: a window showing the Human-Machine Interface.
3. **Agents**: the autonomous agents run in the background, driving the robot.

See how to operate the demo [Operating](operating.md)

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

## GPU-only build

If the host has no NPU, build without FastFlowLM (llama.cpp/Vulkan only):

```bash
WITH_NPU=0 docker compose -f docker/compose.yaml build
```

Before running a GPU-only image, edit `docker/compose.yaml` to:

- remove the `/dev/accel/accel0` device and the `memlock` ulimit (NPU-only), and
- point `config.toml`'s `vlm_safety` endpoint at a `gpu` backend — otherwise `pixi run inference` aborts on the missing NPU engine.

## Troubleshooting

- **O3DE doesn't start / no windows appear**: ensure you ran `xhost +local:root` and that `DISPLAY` is set (`echo $DISPLAY`). Verify your AMD GPU drivers + ROCm container prerequisites are installed.
- **NPU errors / FastFlowLM fails to start**: confirm `/dev/accel/accel0` exists on the host and that the `memlock` ulimit and the device mapping are present in `docker/compose.yaml` (both are required for the NPU).
- **Inference health check fails**: make sure step 3 completed and `models/` (and `models/flm/`) contain the weights `config.toml` references.
- **GPU access / slow or crashing sim**: check your GPU drivers and the [ROCm Docker docs](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/docker.html).
