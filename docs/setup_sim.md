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
pixi run setup
```

This single command runs the full build pipeline in the correct order:

| Step | pixi task          | What it does                                          |
| ---- | ------------------ | ----------------------------------------------------- |
| 1    | `clone-gems`       | `vcs import` for local O3DE gems                      |
| 2    | `clone-ros2-ws`    | `vcs import` for the ROS 2 workspace                  |
| 3    | `install-o3de`     | Install the O3DE engine                               |
| 4    | `register-gems`    | Register O3DE gems                                    |
| 5    | `register-project` | Run `git lfs pull` and register the simulation project|
| 6    | `build-ros2`       | `rosdep install` + `colcon build`                     |
| 7    | `build-sim`        | CMake configure + Ninja build (GameLauncher)          |
| 8    | `sync`             | `uv sync` — install Python dependencies               |


---

### Export Project to Binary

```shell
sudo apt install python3-resolvelib python3-puremagic
cd ${DEMO_ROOT}/sim
bash ./export.sh .
```
