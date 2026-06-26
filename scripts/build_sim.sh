#!/usr/bin/env bash
# Build the O3DE GameLauncher and project assets.
#
# Why this is a script and not an inline pixi task:
#   The O3DE SimulationInterfaces gem does find_package(simulation_interfaces),
#   which is source-built into ros2_ws/install by `build-ros2`. pixi computes the
#   environment activation ONCE at the start of a `pixi run`, so on a clean tree
#   `scripts/setup_env.sh` can't source the overlay (it doesn't exist yet) and
#   build-sim — even though it runs after build-ros2 — never sees it. cmake then
#   fails with "Could not find a package configuration file provided by
#   simulation_interfaces", and only a *second* run works. Sourcing the overlay
#   here, at build time, makes a clean `pixi run -e default setup` succeed on the
#   first try.
set -eo pipefail   # no -u: ROS setup scripts reference unbound vars

# Source the ros2_ws overlay built by build-ros2 so the source-built packages
# (simulation_interfaces, robotnik_*, rai_interfaces) are on CMAKE_PREFIX_PATH.
overlay="$DEMO_ROOT/ros2_ws/install/local_setup.bash"
if [ ! -f "$overlay" ]; then
    echo "ERROR: $overlay not found — run 'pixi run build-ros2' first." >&2
    exit 1
fi
# colcon's setup script can return nonzero mid-source; don't let errexit abort.
set +e
# shellcheck source=/dev/null
source "$overlay"
set -e

cd "$DEMO_ROOT/sim"

# O3DE 26.05 requires C++20 (AzCore headers use `requires`-clauses). The engine
# only sets CMAKE_CXX_STANDARD=20 as a non-FORCE cache default, so a stale build
# dir that cached 17 silently wins and the build fails with "unknown type name
# 'requires'". Pin it explicitly so every configure forces 20.
cmake -B build/linux -G "Ninja Multi-Config" \
    -DCMAKE_MODULE_PATH="$O3DE_ENGINE_PATH/cmake" \
    -DCMAKE_CXX_STANDARD=20 \
    -DLY_DISABLE_TEST_MODULES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DLY_STRIP_DEBUG_SYMBOLS=ON

cmake --build build/linux --config profile \
    --target MobileManipulatorDemo.Assets MobileManipulatorDemo.GameLauncher
