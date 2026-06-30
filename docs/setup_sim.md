# Setup Simulation Environment

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the Project

### Prerequisites

#### Clone the Repository

```shell
git clone git@github.com:RobotecAI/agentic-mobile-manipulator.git
cd agentic-mobile-manipulator
```

#### Install System Dependencies

```bash
sudo apt update
sudo apt install git git-lfs python3-vcstool ninja-build \
    cmake libstdc++-12-dev clang \
    libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 \
    libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev \
    libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev \
    mesa-common-dev libunwind-dev libzstd-dev tix
```

> [!NOTE]
> ROS 2 Jazzy with dev tools (including `colcon`, `rosdep`) must also be installed.
> See the [ROS 2 installation guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional).

#### Install pixi

[pixi](https://pixi.sh) orchestrates all build steps and sets environment variables automatically.

```shell
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your shell or run `source ~/.bashrc` after installation.

---

### Build Everything

```shell
pixi run -e sim setup
```

This single command runs the full build pipeline in the correct order:

| Step | pixi task      | What it does                                        |
| ---- | -------------- | --------------------------------------------------- |
| 1    | `clone`        | `vcs import` + `git lfs pull` for gems and ROS 2 ws |
| 2    | `install-o3de` | Install the O3DE engine                             |
| 3    | `fetch-gems`   | Clone o3de-extras locally, validate all gem paths   |
| 4    | `build-ros2`   | `colcon build` (deps provided by conda/RoboStack)   |
| 5    | `build-sim`    | CMake configure + Ninja build (GameLauncher)        |
| 6    | `sync`         | `uv sync` — install Python dependencies             |

---

### Export Project to Binary

```shell
sudo apt install python3-resolvelib python3-puremagic
cd ${DEMO_ROOT}/sim
bash ./export.sh .
```
