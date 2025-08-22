# Roscon demo 2025

## Building

## Prerequisites

Clone the repository:

```shell
cd /home/${USER}
git clone git@github.com:RobotecAI/golden-hiptage.git
```

Set root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding following line to `.bashrc` or `.zshrc` file:

```shell
export DEMO_ROOT=/home/${USER}/golden-hiptage/
export O3DE_ROOT=${DEMO_ROOT}/engine/o3de
```

## Clone repositories

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/engine.repos
vcs import --input ${DEMO_ROOT}/gems.repos
```

## Setup o3de

Install [packages required to build O3DE:](https://www.docs.o3de.org/docs/welcome-guide/requirements/#linux)

```shell
sudo apt install cmake libstdc++-12-dev clang libglu1-mesa-dev libxcb-randr0-dev libxcb-xinerama0 libxcb-xinput0 libxcb-xinput-dev libxcb-xfixes0-dev libxcb-xkb-dev libxkbcommon-dev libxkbcommon-x11-dev libfontconfig1-dev libpcre2-16-0 zlib1g-dev mesa-common-dev libunwind-dev libzstd-dev tix
```

```shell
cd ${O3DE_ROOT}
git lfs install
git lfs pull
python/get_python.sh
${O3DE_ROOT}/scripts/o3de.sh register --this-engine
```

We recommend cherry-pick of those bug fixes (for version 2510):

```shell
cd ${O3DE_ROOT}
git cherry-pick 57680ee42f18d5952e4d4fa5ab52750edefb878e #o3de/o3de#19164
git cherry-pick d27e655b7a66255140cb766854e2bcb9007170d3 #o3de/o3de#18830
```

## Setup o3de-extras

```shell
cd ${DEMO_ROOT}/gems
git lfs install
git lfs pull
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path  ${DEMO_ROOT}/gems/o3de-extras/Gems
```

## Non-canonical gems

Those are gems that are open source, but not maintained by O3DF.

```shell
cd  ${DEMO_ROOT}/gems
${O3DE_ROOT}/scripts/o3de.sh register --gem-path ${DEMO_ROOT}/gems/o3de-humanworker-gem
${O3DE_ROOT}/scripts/o3de.sh register --gem-path ${DEMO_ROOT}/gems/o3de-ur-robots-gem
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-warehouse-assets
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-o3de-tools
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/project_gems/

```

## Register project

```shell
${O3DE_ROOT}/scripts/o3de.sh register  --project-path ${DEMO_ROOT}/sim
```

## ROS2 workspace

Clone needed packages:

```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/ros2_ws.repos
```

```shell
cd ${DEMO_ROOT}/ros2_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```

Source the installation to `.bashrc` or `.zshrc` file:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
```

## Build Editor and toolset

```shell
${DEMO_ROOT}/sim
cmake -B build/linux -G "Ninja Multi-Config" \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=ON \
    -DCMAKE_LINKER_TYPE=MOLD
cmake --build build/linux --config profile --target MobileManipulatorDemo Editor MobileManipulatorDemo.Assets
```

# Export project

It is optional step to create a standalone package of the project.

```shell
${O3DE_ROOT}/scripts/o3de.sh export-project \
    --project-path ${DEMO_ROOT}/sim  \
    -cca "-DCMAKE_LINKER_TYPE=DEFAULT -DLY_UNITY_BUILD=ON"
```

# Running ROS 2 sample scripts

```shell
ros2 launch robotec_kairos_ur10 robotec_launch.py
```

## Slam exercise

```shell
ros2 launch robotec_kairos_ur10 robotec_slam_toolbox.launch.py
```

## Nav2

```shell
ros2 launch robotec_kairos_ur10 robotec_nav2.launch.py
```

## pre-commit

```shell
pre-commit install
```
