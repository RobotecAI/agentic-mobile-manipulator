#!/usr/bin/env bash
# Sourced by pixi on environment activation.
# Sets up O3DE and ROS 2 environment variables automatically.

# ── O3DE engine path ─────────────────────────────────────────────────────────
# Only the SDK unpacked by install_o3de.sh is used; a system-wide O3DE install
# (e.g. /opt/O3DE) is ignored. build_sim.sh passes this path to CMake explicitly.
# O3DE binaries get their library path from scripts/o3de_exec.sh.
export O3DE_VERSION="${O3DE_VERSION:-26.05}"
export O3DE_HOME="${O3DE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/o3de}"
export O3DE_ENGINE_PATH="$O3DE_HOME/$O3DE_VERSION"

# ── ROS 2 setup ──────────────────────────────────────────────────────────────
if [[ -f "/opt/ros/jazzy/local_setup.sh" ]]; then
    # shellcheck source=/dev/null
    source "/opt/ros/jazzy/local_setup.sh"
fi

# Project ROS 2 workspace (available after `pixi run build-ros2`)
if [[ -f "${PIXI_PROJECT_ROOT}/ros2_ws/install/local_setup.sh" ]]; then
    # shellcheck source=/dev/null
    source "${PIXI_PROJECT_ROOT}/ros2_ws/install/local_setup.sh"
fi
