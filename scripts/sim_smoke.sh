#!/usr/bin/env bash
# Headless smoke test for the O3DE sim.
#
# Boots the GameLauncher with the null renderer (--rhi=null) — no GPU, no X
# display needed — and passes if the simulation is actually *ticking*, proven by
# catching a message on /clock within a timeout. That single check exercises the
# whole cold path: binary runs, assets + level load, PhysX ticks, and the ROS 2
# bridge publishes.
#
# NOT checked: camera / rendered sensors. Those need the Atom (Vulkan) renderer,
# which headless needs a DRI3-capable display for — Xvfb doesn't provide DRI3, so
# the GPU+Vulkan path wedges on swapchain creation. rhi=null has no renderer at
# all, so camera topics are advertised but never publish. Verifying rendered
# output headless is a separate, unsolved problem; keep it out of the fast gate.
#
# Run:        pixi run sim-smoke
# In Docker:  docker run --rm --entrypoint pixi <o3de-image> run sim-smoke
# Tune:       SIM_SMOKE_TIMEOUT=120 pixi run sim-smoke
#             SIM_SMOKE_TOPIC=/joint_states SIM_SMOKE_TYPE=sensor_msgs/msg/JointState pixi run sim-smoke
set -uo pipefail

# Hermetic: only ever see our own sim on loopback, so a neighbouring sim on a
# shared CI runner can't cause a false pass.
export ROS_LOCALHOST_ONLY=1

LAUNCHER="${DEMO_ROOT:-$PWD}/sim/build/linux/bin/profile/MobileManipulatorDemo.GameLauncher"
TIMEOUT="${SIM_SMOKE_TIMEOUT:-90}"      # boot + first message; rhi=null is faster than Vulkan
TOPIC="${SIM_SMOKE_TOPIC:-/clock}"
# Type must be explicit: with no publisher up yet, `ros2 topic echo` can't infer
# the type from the graph and bails instantly instead of waiting.
TYPE="${SIM_SMOKE_TYPE:-rosgraph_msgs/msg/Clock}"
LOG="$(mktemp)"

[ -x "$LAUNCHER" ] || { echo "[FAIL] launcher not built: $LAUNCHER"; exit 1; }

# GameLauncher ignores SIGINT (won't stop on Ctrl+C), so hard-kill on exit.
# Kill the captured PID, plus a pkill by full command line as a fallback (the
# comm name isn't reliably set during early boot). pkill -f is safe: this shell's
# own argv is just "bash scripts/sim_smoke.sh", so it can't match itself.
LAUNCHER_PID=""
cleanup() {
  [ -n "$LAUNCHER_PID" ] && kill -9 "$LAUNCHER_PID" 2>/dev/null
  pkill -9 -f 'MobileManipulatorDemo.GameLauncher' 2>/dev/null
}
trap cleanup EXIT

echo "[smoke] launching sim headless (--rhi=null)"
env -u DISPLAY "$LAUNCHER" -bg_ConnectToAssetProcessor=0 --rhi=null >"$LOG" 2>&1 &
LAUNCHER_PID=$!

# /clock is published BEST_EFFORT; a default (reliable) subscriber gets nothing.
echo "[smoke] waiting up to ${TIMEOUT}s for a message on ${TOPIC} (${TYPE})"
if timeout "$TIMEOUT" ros2 topic echo --once --qos-reliability best_effort "$TOPIC" "$TYPE" >/dev/null 2>&1; then
  echo "[PASS] ${TOPIC} is publishing — sim ticks headless"
  exit 0
fi

echo "[FAIL] no message on ${TOPIC} within ${TIMEOUT}s"
echo "----- last 30 log lines -----"
tail -30 "$LOG"
exit 1
