# Running the Demo

## O3DE

To run the O3DE, run the following command:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
${DEMO_ROOT}/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher
```

## ROS 2

To run the ROS 2 stack and control agents, execute:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
./scripts/run_ros2_stack.sh
```

## HMI

To run the HMI, execute:

```shell
source ${DEMO_ROOT}/ros2_ws/install/setup.bash
ros2 launch mobile_manipulator_hmi hmi_launch.py
```

## Agent

For instructions, see: [Agent setup and inference](../rai_app/README.md)
