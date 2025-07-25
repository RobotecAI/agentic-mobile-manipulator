# Roscon demo 2025

## Building 

## Prerequisites
Set root directory of the project to `$DEMO_ROOT` and `$O3DE_ROOT`, e.g., by adding following line to `.bashrc` or `.zshrc` file:
```shell
export DEMO_ROOT=/home/${USER}/MobileManipulatorDemo/
export O3DE_ROOT=${DEMO_ROOT}/engine/o3de
```

## Clone repositories
```shell
cd ${DEMO_ROOT}
vcs import --input ${DEMO_ROOT}/engine.repos
vcs import --input ${DEMO_ROOT}/gems.repos
```

## Setup o3de
```shell
cd ${O3DE_ROOT}
git lfs install
git lfs pull
python/get_python.sh
${O3DE_ROOT}/scripts/o3de.sh register --this-engine
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
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/gems/robotec-o3de-tools
${O3DE_ROOT}/scripts/o3de.sh register --all-gems-path ${DEMO_ROOT}/project_gems/

```
## Register project 

```shell
${O3DE_ROOT}/scripts/o3de.sh register  --project-path ${DEMO_ROOT}/sim
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


# ROS2 workspace

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

## Running sample script
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

