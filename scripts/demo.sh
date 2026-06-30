#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()     { echo -e "  ${GREEN}●${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}!${RESET} $*"; }
err()     { echo -e "  ${RED}✗${RESET} $*" >&2; }
ok()      { echo -e "  ${GREEN}✓${RESET} $*"; }
section() { echo -e "\n${BOLD}${CYAN}$*${RESET}"; }

# ── Helpers ───────────────────────────────────────────────────────────────────

wait_topic() {
    local topic="$1" timeout="${2:-120}" elapsed=0 dots=""
    echo -ne "  ${YELLOW}○${RESET} Waiting for ${topic}"
    while ! ros2 topic list 2>/dev/null | grep -q "^${topic}$"; do
        sleep 2; elapsed=$((elapsed + 2)); dots="${dots}."; echo -n "."
        if [ $elapsed -ge $timeout ]; then
            printf " ${RED}✗${RESET}\n"
            err "Timed out waiting for ${topic} (${timeout}s)"
            return 1
        fi
    done
    printf "\r  ${GREEN}●${RESET} Waiting for ${topic}%s ${GREEN}✓${RESET}\n" "$dots"
}

check_inference() {
    log "Waiting 10s for inference servers to initialize..."
    sleep 10
    if bash "$DEMO_ROOT/scripts/smoke_test.sh"; then
        return 0
    else
        echo ""
        warn "Inference servers not healthy. Inspect with: pixi run serve-all"
        return 1
    fi
}

stop_all() {
    for s in simulation inference agent; do
        tmux kill-session -t "$s" 2>/dev/null || true
    done
}

# ── Guard ─────────────────────────────────────────────────────────────────────

for s in simulation inference agent; do
    if tmux has-session -t "$s" 2>/dev/null; then
        warn "Session '$s' already exists."
        warn "Run 'pixi run demo-stop' first, or attach with: tmux attach -t $s"
        exit 1
    fi
done

trap 'echo; warn "Interrupted — cleaning up..."; stop_all; exit 1' INT TERM QUIT

# ── 1. Simulation ─────────────────────────────────────────────────────────────

section "Starting simulation..."

# Create the session with a named first window so we don't rely on window index numbers
tmux new-session -d -s simulation -n "sim+ros2" -x 220 -y 50
SIM_TOP_PANE=$(tmux display-message -p -t simulation:sim+ros2 "#{pane_id}")
SIM_BOTTOM_PANE=$(tmux split-window -v -P -F "#{pane_id}" -t "$SIM_TOP_PANE")

# Send commands to the panes using pane IDs so pane-base-index does not matter
tmux send-keys -t "$SIM_TOP_PANE" "cd $DEMO_ROOT && pixi run sim" Enter
log "O3DE launched  (simulation — top pane)"

wait_topic "/clock" 120 || { stop_all; exit 1; }

# ── 2. ROS 2 Stack ────────────────────────────────────────────────────────────

section "Starting ROS 2 stack..."

tmux send-keys -t "$SIM_BOTTOM_PANE" "cd $DEMO_ROOT && pixi run ros2" Enter
log "ROS 2 stack launched  (simulation — bottom pane)"

wait_topic "/joint_states" 60 || { stop_all; exit 1; }

# ── 3. Inference servers ──────────────────────────────────────────────────────

section "Starting inference servers..."

# One pane per inference server (config.toml SSOT). Both VLMs run:
# vlm_safety (npu) and vlm_inspection (gpu).
tmux new-session -d -s inference -n models -x 220 -y 50
INF_TASKS=(serve-llm serve-vlm-safety serve-vlm-inspection serve-embedding serve-reranker)
first_pane=$(tmux display-message -p -t inference:models "#{pane_id}")
tmux send-keys -t "$first_pane" "cd $DEMO_ROOT && pixi run ${INF_TASKS[0]}" Enter
for task in "${INF_TASKS[@]:1}"; do
    pane=$(tmux split-window -P -F "#{pane_id}" -t inference:models)
    tmux select-layout -t inference:models tiled
    tmux send-keys -t "$pane" "cd $DEMO_ROOT && pixi run $task" Enter
done
tmux select-layout -t inference:models tiled
log "Inference session created  (inference — ${#INF_TASKS[@]} panes)"

check_inference || { stop_all; exit 1; }

# ── 4. Agents + Orchestrator ──────────────────────────────────────────────────

section "Starting agents + orchestrator..."

# agent session: agents (top pane) + orchestrator (bottom pane)
tmux new-session -d -s agent -n agents -x 220 -y 50
AGENT_TOP=$(tmux display-message -p -t agent:agents "#{pane_id}")
AGENT_BOTTOM=$(tmux split-window -v -P -F "#{pane_id}" -t "$AGENT_TOP")
tmux send-keys -t "$AGENT_TOP" "cd $DEMO_ROOT && pixi run agents" Enter
tmux send-keys -t "$AGENT_BOTTOM" "cd $DEMO_ROOT && pixi run orchestrator" Enter
log "Agents + orchestrator launched  (agent)"

# ── Final health check ───────────────────────────────────────────────────────

section "Running health check in 10s..."
sleep 10

failed=false

for s in simulation inference agent; do
    if tmux has-session -t "$s" 2>/dev/null; then
        ok "Session '$s' is running"
    else
        err "Session '$s' has exited unexpectedly"
        failed=true
    fi
done

while read -r url; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        ok "Inference $url — OK"
    else
        err "Inference $url — not responding (HTTP $code)"
        failed=true
    fi
done < <(python -m rai_app.inference.serve --health 2>/dev/null)

for topic in /clock /joint_states; do
    if ros2 topic list 2>/dev/null | grep -q "^${topic}$"; then
        ok "Topic ${topic} — OK"
    else
        err "Topic ${topic} — not found"
        failed=true
    fi
done

# ── Result ────────────────────────────────────────────────────────────────────

if $failed; then
    echo ""
    echo -e "${BOLD}${RED}=== Demo failed — stopping all sessions ===${RESET}"
    echo ""
    stop_all
    exit 1
fi

echo ""
echo -e "${BOLD}${GREEN}=== Demo running ===${RESET}"
echo ""
echo -e "  ${CYAN}tmux attach -t simulation${RESET}   — O3DE sim (top) + ROS 2 stack (bottom)"
echo -e "  ${CYAN}tmux attach -t inference${RESET}    — inference servers (one pane each)"
echo -e "  ${CYAN}tmux attach -t agent${RESET}        — agents (top) + orchestrator (bottom)"
echo ""
echo -e "  Stop everything:  ${YELLOW}pixi run demo-stop${RESET}"
echo ""
