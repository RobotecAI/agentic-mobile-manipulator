#!/usr/bin/env bash
set -e

source /root/MobileManipulatorDemo/ros2_ws/install/setup.bash

exec /root/MobileManipulatorDemo/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher \
  -bg_ConnectToAssetProcessor=0
