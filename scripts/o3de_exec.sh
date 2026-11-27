#!/usr/bin/env bash
# Run an O3DE binary with the SDK, project and pixi libraries on the loader path.
# Only O3DE processes get this path: O3DE ships its own patched Qt5 and other
# libs, and putting them on everyone's LD_LIBRARY_PATH breaks ROS 2 tools.
set -euo pipefail
: "${O3DE_ENGINE_PATH:?O3DE_ENGINE_PATH is not set. Run: pixi run install-o3de}"
export LD_LIBRARY_PATH="$O3DE_ENGINE_PATH/bin/Linux/profile/Default:${DEMO_ROOT:-$PIXI_PROJECT_ROOT}/sim/build/linux/bin/profile:$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$@"
