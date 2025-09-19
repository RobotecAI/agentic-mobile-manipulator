# Setup HMI Environment

The contents of this repository are compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the GUI

```shell
cd ${DEMO_ROOT}/ros2_ws/
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```
