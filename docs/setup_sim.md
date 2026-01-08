# Setup Simulation Environment

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the Project

### Prerequisites

#### Clone the Repository

```shell
cd /home/${USER}
git clone git@github.com:RobotecAI/MobileManipulatorDemo.git
```

#### Set the Root Directory of the Project

Set the root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding the following lines to your `.bashrc` or `.zshrc` file:

```shell
export DEMO_ROOT=/home/${USER}/MobileManipulatorDemo/
export O3DE_ROOT=${DEMO_ROOT}engine/o3de
```

#### Install Base Dependencies

```bash
sudo apt update
sudo apt install git git-lfs ninja-build
```

#### Clone Repositories

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/engine.repos
vcs import --input ${DEMO_ROOT}/gems.repos
vcs import --input ${DEMO_ROOT}/ros2_ws.repos
```

### Setup O3DE

Install [packages required to build O3DE:](https://www.docs.o3de.org/docs/welcome-guide/requirements/#linux)

```shell
sudo apt install cmake libstdc++-12-dev clang libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev mesa-common-dev libunwind-dev libzstd-dev tix
```

Register the O3DE engine:

```shell
cd ${O3DE_ROOT}
git lfs install
git lfs pull
python/get_python.sh
${O3DE_ROOT}/scripts/o3de.sh register --this-engine
```

#### Setup o3de-extras

```shell
cd ${DEMO_ROOT}/gems
git lfs install
git lfs pull
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path  ${DEMO_ROOT}/gems/o3de-extras/Gems
```

#### Non-canonical Gems

These are gems that are open source but not maintained by O3DE.

```shell
cd  ${DEMO_ROOT}/gems
${O3DE_ROOT}/scripts/o3de.sh register --gem-path ${DEMO_ROOT}/gems/o3de-humanworker-gem
${O3DE_ROOT}/scripts/o3de.sh register --gem-path ${DEMO_ROOT}/gems/o3de-ur-robots-gem
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-warehouse-assets
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-generic-assets
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-o3de-tools
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/project_gems/

```

#### Register Project

```shell
${O3DE_ROOT}/scripts/o3de.sh register  --project-path ${DEMO_ROOT}/sim
```

### Setup ROS 2

#### Build the ROS 2 Workspace

```shell
cd ${DEMO_ROOT}/ros2_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --packages-select simulation_interfaces
```

Source the installation in your `.bashrc` or `.zshrc` file:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

### Build O3DE Editor and GameLauncher

```shell
cd ${DEMO_ROOT}/sim
cmake -B build/linux -G "Ninja Multi-Config" \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=ON \
    -DCMAKE_LINKER_TYPE=MOLD
cmake --build build/linux --config profile --target MobileManipulatorDemo Editor MobileManipulatorDemo.Assets MobileManipulatorDemo.GameLauncher
```

### Export project to binary file

```shell
sudo apt install python3-resolvelib python3-puremagic
cd ${DEMO_ROOT}/sim
bash ./export.sh .
```
