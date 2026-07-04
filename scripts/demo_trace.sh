#!/usr/bin/env bash
# Unattended trace run:
#   1. bring up the full demo (sim + stack + inference + agents + HMI)
#   2. populate the scene
#   3. send ONE task to the orchestrator
#   4. wait for it to finish
#   5. leave the agentic conversation trace in a run dir, then kill everything
#
# The conversation itself is written by ConversationFileCallback inside the
# orchestrator process (rai_app/agents/callbacks.py), so this script only drives
# the lifecycle. Run it in the ROS env, e.g.:
#   pixi run -e single-pc-gpu-and-npu bash scripts/demo_trace.sh
#
# Env knobs:
#   TASK       task string sent to /user_tasks
#              (default: prepare shipment of one CPU)
#   TRACE_DIR  where the trace lands (default: runs/<timestamp>)
#   MAX_WAIT   hard cap in seconds on task execution (default: 900)
#   IDLE       seconds of trace inactivity treated as "done" fallback (default: 180)
#   SKIP_SCENE set to 1 to skip scene population
set -euo pipefail

DEMO_ROOT="${DEMO_ROOT:-$(pwd)}"
TASK="${TASK:-Prepare shipping of the following items: one CPU, }"
TS="$(date +%Y-%m-%d_%H-%M-%S)"
TRACE_DIR="${TRACE_DIR:-$DEMO_ROOT/runs/$TS}"
MAX_WAIT="${MAX_WAIT:-900}"
IDLE="${IDLE:-180}"
AGENTS_SESSION="agentic-mobile-manipulator-agents"
LOG="$TRACE_DIR/log.txt"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
log()  { echo -e "  ${GREEN}●${RESET} $*"; }
warn() { echo -e "  ${YELLOW}!${RESET} $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*" >&2; }

# The orchestrator (a tmux pane that re-enters pixi) inherits the tmux server's
# environment, so export the trace location before any session is created.
export AMM_TRACE=1
export AMM_TRACE_DIR="$TRACE_DIR"
mkdir -p "$TRACE_DIR"

cleanup() {
    warn "Tearing down..."
    bash "$DEMO_ROOT/scripts/kill_sessions.sh" || true
    # O3DE GameLauncher ignores SIGINT and can outlive its tmux session.
    pkill -9 -f 'MobileManipulatorDemo.GameLauncher' 2>/dev/null || true
}
trap 'echo; warn "Interrupted"; cleanup; exit 1' INT TERM

# ── 0. Clean tmux server so our env (history-limit, AMM_TRACE_DIR) is inherited ──
tmux kill-server 2>/dev/null || true
tmux start-server
tmux set -g history-limit 50000

# ── 1. Full demo ────────────────────────────────────────────────────────────
echo -e "${BOLD}Starting demo (trace -> $TRACE_DIR)${RESET}"
bash "$DEMO_ROOT/scripts/demo.sh"

# ── 2. Populate the scene ───────────────────────────────────────────────────
if [ "${SKIP_SCENE:-0}" != "1" ]; then
    log "Populating scene (/rai/scene/standard)..."
    ros2 service call /rai/scene/standard std_srvs/srv/Trigger "{}" >/dev/null
    log "Scene populated."
fi

# ── 3. Send the task ────────────────────────────────────────────────────────
log "Sending task: $TASK"
before_size=$(wc -c <"$LOG" 2>/dev/null || echo 0)
ros2 topic pub --once /user_tasks std_msgs/msg/String "{data: '${TASK//\'/\'\\\'\'}'}" >/dev/null

# ── 4. Wait for completion ──────────────────────────────────────────────────
# Prefer the precise marker the callback writes on the root chain end; fall back
# to trace inactivity, then to the hard MAX_WAIT cap.
log "Waiting for task to finish (max ${MAX_WAIT}s, idle ${IDLE}s)..."
started=false
waited=0
while [ "$waited" -lt "$MAX_WAIT" ]; do
    if grep -q "TASK COMPLETE" "$LOG" 2>/dev/null; then
        log "Task complete (marker)."
        break
    fi
    if tmux capture-pane -pJ -S - -t "$AGENTS_SESSION" 2>/dev/null | grep -q "Finished task:"; then
        log "Task complete (orchestrator log)."
        break
    fi
    cur_size=$(wc -c <"$LOG" 2>/dev/null || echo 0)
    if [ "$cur_size" -gt "$before_size" ]; then started=true; fi
    if $started; then
        # idle = no trace growth for IDLE seconds
        last_mtime=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
        now=$(date +%s)
        if [ $((now - last_mtime)) -ge "$IDLE" ]; then
            warn "No trace activity for ${IDLE}s — assuming done."
            break
        fi
    fi
    sleep 5; waited=$((waited + 5))
done
[ "$waited" -ge "$MAX_WAIT" ] && warn "Hit MAX_WAIT (${MAX_WAIT}s) — dumping and stopping."

# ── 5. Snapshot orchestrator pane, then tear down ───────────────────────────
tmux capture-pane -pJ -S - -t "$AGENTS_SESSION" >"$TRACE_DIR/agents_pane.log" 2>/dev/null || true
{
    echo "task: $TASK"
    echo "started: $TS"
    echo "finished: $(date +%Y-%m-%d_%H-%M-%S)"
} >"$TRACE_DIR/manifest.txt"

cleanup
trap - INT TERM

echo ""
echo -e "${BOLD}${GREEN}=== Trace saved ===${RESET}"
echo -e "  ${BOLD}$TRACE_DIR${RESET}"
echo "    log.txt        human-readable conversation (orchestrator + subagents)"
echo "    trace.jsonl    one JSON record per event"
echo "    agents_pane.log raw agents tmux output"
echo "    manifest.txt   task + timestamps"
