#!/usr/bin/env bash
# Sourced by pixi on environment activation.
# Sets up O3DE and ROS 2 environment variables automatically.

# ── O3DE engine path ─────────────────────────────────────────────────────────
# Resolved in order:
#   1. Caller-set O3DE_ENGINE_PATH (CI override / native dev workflow)
#   2. engine_path from sim/user/project.json — written by install_o3de.sh,
#      mirrors what EngineFinder.cmake (Option 2) uses at configure time
#   3. /opt/O3DE/<version> fallback for a fresh checkout before install runs
if [[ -z "${O3DE_ENGINE_PATH:-}" ]]; then
    user_project_json="${PIXI_PROJECT_ROOT:-.}/sim/user/project.json"
    if [[ -f "$user_project_json" ]]; then
        O3DE_ENGINE_PATH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('engine_path',''))" "$user_project_json" 2>/dev/null || true)
    fi
    export O3DE_ENGINE_PATH="${O3DE_ENGINE_PATH:-/opt/O3DE/26.05}"
fi

# ── LD_LIBRARY_PATH: O3DE bundled libs take precedence over conda ────────────
# Pixi/conda activation injects conda's lib dir into LD_LIBRARY_PATH. O3DE
# ships its own patched Qt5 and other runtime libs; when conda's copies shadow
# them the linker resolves mismatched ABIs (e.g. Qt_5_PRIVATE_API undefined
# symbol). Prepending the O3DE lib dir ensures the bundled libs always win.
export LD_LIBRARY_PATH="$O3DE_ENGINE_PATH/bin/Linux/profile/Default${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

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
