#!/usr/bin/env bash
# Sourced by pixi on environment activation.
# Sets up ROS 2 Jazzy paths so that pixi shell / pixi run tasks have a full
# ROS 2 environment without needing manual `source` calls.

# O3DE SDK path — resolved in order:
#   1. Caller-set env var (native dev workflow)
#   2. /etc/o3de-engine-path written by the container build (actual install path)
#   3. Hardcoded fallback for a typical native install
if [[ -z "$O3DE_ENGINE_PATH" ]]; then
    if [[ -f /etc/o3de-engine-path ]]; then
        export O3DE_ENGINE_PATH=$(cat /etc/o3de-engine-path)
    else
        export O3DE_ENGINE_PATH=/opt/O3DE/26.05
    fi
fi

# Base ROS 2 installation
if [ -f "/opt/ros/jazzy/local_setup.sh" ]; then
    # shellcheck source=/dev/null
    source "/opt/ros/jazzy/local_setup.sh"
fi

# Project ROS 2 workspace (available after `pixi run build-ros2`)
if [ -f "${PIXI_PROJECT_ROOT}/ros2_ws/install/local_setup.sh" ]; then
    # shellcheck source=/dev/null
    source "${PIXI_PROJECT_ROOT}/ros2_ws/install/local_setup.sh"
fi
