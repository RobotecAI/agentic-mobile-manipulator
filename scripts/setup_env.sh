#!/usr/bin/env bash
# Sourced by pixi on environment activation.
# Sets up ROS 2 Jazzy paths so that pixi shell / pixi run tasks have a full
# ROS 2 environment without needing manual `source` calls.

# O3DE SDK path — resolved in order:
#   1. Caller-set env var (native dev workflow)
#   2. Discovered from /opt/O3DE/ (set by install_o3de.sh or container build)
if [[ -z "$O3DE_ENGINE_PATH" ]]; then
    discovered=$(ls -d /opt/O3DE/*/ 2>/dev/null | sort -V | tail -1 | sed 's:/$::')
    [[ -n "$discovered" ]] && export O3DE_ENGINE_PATH="$discovered"
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
