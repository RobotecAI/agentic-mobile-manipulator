#!/usr/bin/env bash
set -e

source /root/MobileManipulatorDemo/ros2_ws/install/setup.bash

exec ros2 launch mobile_manipulator_hmi hmi_launch.py & /root/MobileManipulatorDemo/run_ros2_stack.sh
