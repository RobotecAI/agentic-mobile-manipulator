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
#   pixi run -e single-pc-gpu-and-npu demo-trace
#
# Env knobs:
#   TASK       task string sent to /user_tasks (default: prepare one CPU shipment)
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

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
log()  { echo -e "  ${GREEN}●${RESET} $*"; }
warn() { echo -e "  ${YELLOW}!${RESET} $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*" >&2; }
# Byte size of a file, or 0 if it doesn't exist yet (log.txt is created lazily on
# the orchestrator's first LLM event, i.e. only after the task starts).
filesize() { [ -f "$1" ] && wc -c <"$1" || echo 0; }

# The orchestrator (a tmux pane that re-enters pixi) inherits its environment from
# the tmux server, which the demo's first `tmux new-session` starts with THIS
# script's env — so exporting the trace location here is enough. (Same mechanism
# demo.sh already uses for AMM_NO_ATTACH.) No tmux-server surgery needed.
export AMM_TRACE=1
export AMM_TRACE_DIR="$TRACE_DIR"

cleanup() {
    warn "Tearing down..."
    bash "$DEMO_ROOT/scripts/kill_sessions.sh" || true
    # O3DE GameLauncher ignores SIGINT and can outlive its tmux session.
    pkill -9 -f 'MobileManipulatorDemo.GameLauncher' 2>/dev/null || true
}
trap 'echo; warn "Interrupted"; cleanup; exit 1' INT TERM

# ── 1. Full demo ────────────────────────────────────────────────────────────
echo -e "${BOLD}Starting demo (trace -> $TRACE_DIR)${RESET}"
bash "$DEMO_ROOT/scripts/demo.sh"

# The callback creates the trace dir on orchestrator startup. Prefer our
# predicted dir; if env somehow didn't propagate (e.g. a pre-existing tmux
# server), fall back to the newest runs/* dir.
resolve_trace_dir() {
    if [ ! -d "$TRACE_DIR" ]; then
        local dirs
        shopt -s nullglob
        dirs=("$DEMO_ROOT"/runs/*/)
        shopt -u nullglob
        if [ ${#dirs[@]} -gt 0 ]; then
            # timestamp dir names sort chronologically; newest is last.
            local newest
            newest=$(printf '%s\n' "${dirs[@]}" | sort | tail -1)
            TRACE_DIR="${newest%/}"
        fi
    fi
    LOG="$TRACE_DIR/log.txt"
}

# ── 2. Wait for the orchestrator to be ready to receive tasks ───────────────
log "Waiting for orchestrator to subscribe to /user_tasks..."
ready=false
for _ in $(seq 1 60); do
    if ros2 topic info /user_tasks 2>/dev/null | grep -qE "Subscription count: [1-9]"; then
        ready=true; break
    fi
    sleep 2
done
$ready || { err "Orchestrator never subscribed to /user_tasks"; cleanup; exit 1; }
log "Orchestrator ready."

# ── 3. Populate the scene ───────────────────────────────────────────────────
if [ "${SKIP_SCENE:-0}" != "1" ]; then
    log "Populating scene (/rai/scene/standard)..."
    ros2 service call /rai/scene/standard std_srvs/srv/Trigger "{}" >/dev/null
    log "Scene populated."
fi

# ── 4. Send the task ────────────────────────────────────────────────────────
resolve_trace_dir
log "Sending task: $TASK"
before_size=$(filesize "$LOG")
ros2 topic pub --once /user_tasks std_msgs/msg/String "{data: '${TASK//\'/\'\\\'\'}'}" >/dev/null

# ── 5. Wait for completion ──────────────────────────────────────────────────
# Prefer the precise marker the callback writes on the root chain end; fall back
# to trace inactivity, then to the hard MAX_WAIT cap.
log "Waiting for task to finish (max ${MAX_WAIT}s, idle ${IDLE}s)..."
started=false
waited=0
while [ "$waited" -lt "$MAX_WAIT" ]; do
    if grep -q "TASK COMPLETE" "$LOG" 2>/dev/null; then
        log "Task complete (marker)."; break
    fi
    if tmux capture-pane -pJ -S - -t "$AGENTS_SESSION" 2>/dev/null | grep -q "Finished task:"; then
        log "Task complete (orchestrator log)."; break
    fi
    cur_size=$(filesize "$LOG")
    [ "$cur_size" -gt "$before_size" ] && started=true
    if $started; then
        last_mtime=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
        now=$(date +%s)
        if [ $((now - last_mtime)) -ge "$IDLE" ]; then
            warn "No trace activity for ${IDLE}s — assuming done."; break
        fi
    fi
    sleep 5; waited=$((waited + 5))
done
[ "$waited" -ge "$MAX_WAIT" ] && warn "Hit MAX_WAIT (${MAX_WAIT}s) — dumping and stopping."

# ── 6. Snapshot orchestrator pane, then tear down ───────────────────────────
mkdir -p "$TRACE_DIR"
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
echo "    log.txt         human-readable conversation (orchestrator + subagents)"
echo "    trace.jsonl     one JSON record per event"
echo "    agents_pane.log raw agents tmux output"
echo "    manifest.txt    task + timestamps"
