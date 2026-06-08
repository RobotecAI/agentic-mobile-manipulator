#!/usr/bin/env bash
# Sourced by pixi on environment activation.
# Sets up ROS 2 Jazzy paths so that pixi shell / pixi run tasks have a full
# ROS 2 environment without needing manual `source` calls.

# Base ROS 2 installation
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    # shellcheck source=/dev/null
    source "/opt/ros/jazzy/setup.bash"
fi

# Project ROS 2 workspace (available after `pixi run build-ros2`)
if [ -f "${DEMO_ROOT}/ros2_ws/install/setup.bash" ]; then
    # shellcheck source=/dev/null
    source "${DEMO_ROOT}/ros2_ws/install/setup.bash"
fi
