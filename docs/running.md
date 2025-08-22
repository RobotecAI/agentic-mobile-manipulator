# Running a demo

## O3DE

To run the O3DE, run the following command and choose `DemoLevel.prefab` from the level menu.

1. Open the editor

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
${DEMO_ROOT}/sim/build/linux/bin/profile/Editor
```

2. Choose `DemoLevel.prefab` from the level menu

3. Run the GameMode (ctrl+g)

## ROS 2

Run the ROS 2 stack:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch robotec_kairos_ur10 robotec_launch.py
```

## Agent

Run the agent:

```shell
cd ${DEMO_ROOT}
uv run python agent/agent.py
```
