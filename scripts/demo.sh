#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Each component runs in its own tmux session (created by its `pixi run` task).
# AMM_NO_ATTACH tells those launchers to start the session detached and return
# instead of attaching, so this script can drive them in sequence.
export AMM_NO_ATTACH=1
SIM_SESSION="agentic-mobile-manipulator-sim"
STACK_SESSION="agentic-mobile-manipulator-stack"
INF_SESSION="agentic-mobile-manipulator-llm-servers"
AGENTS_SESSION="agentic-mobile-manipulator-agents"
HMI_SESSION="agentic-mobile-manipulator-hmi"
ALL_SESSIONS=("$SIM_SESSION" "$STACK_SESSION" "$INF_SESSION" "$AGENTS_SESSION" "$HMI_SESSION")

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
        warn "Inference servers not healthy. Inspect with: pixi run inference"
        return 1
    fi
}

stop_all() { bash "$DEMO_ROOT/scripts/kill_sessions.sh"; }

# ── Guard ─────────────────────────────────────────────────────────────────────

for s in "${ALL_SESSIONS[@]}"; do
    if tmux has-session -t "$s" 2>/dev/null; then
        warn "Session '$s' already exists."
        warn "Run 'pixi run kill' first, or attach with: tmux attach -t $s"
        exit 1
    fi
done

trap 'echo; warn "Interrupted — cleaning up..."; stop_all; exit 1' INT TERM QUIT

# ── 1. Simulation ─────────────────────────────────────────────────────────────

section "Starting simulation..."
pixi run sim
log "O3DE launched  ($SIM_SESSION)"
wait_topic "/clock" 120 || { stop_all; exit 1; }

# ── 2. ROS 2 Stack ────────────────────────────────────────────────────────────

section "Starting ROS 2 stack..."
pixi run stack
log "ROS 2 stack launched  ($STACK_SESSION)"
wait_topic "/joint_states" 60 || { stop_all; exit 1; }

# ── 3. Inference servers ──────────────────────────────────────────────────────

section "Starting inference servers..."
# One pane per local endpoint (config.toml SSOT). Both VLMs run:
# vlm_safety (npu) and vlm_inspection (gpu).
pixi run inference
log "Inference servers launched  ($INF_SESSION)"
check_inference || { stop_all; exit 1; }

# ── 4. Agents + Orchestrator ──────────────────────────────────────────────────

section "Starting agents + orchestrator..."
pixi run agents
log "Agents + orchestrator launched  ($AGENTS_SESSION)"

# ── 5. HMI ────────────────────────────────────────────────────────────────────

section "Starting HMI..."
pixi run hmi
log "HMI launched  ($HMI_SESSION)"

# ── Final health check ───────────────────────────────────────────────────────

section "Running health check in 10s..."
sleep 10

failed=false

for s in "${ALL_SESSIONS[@]}"; do
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
echo -e "  ${CYAN}tmux attach -t $SIM_SESSION${RESET}      — O3DE simulation"
echo -e "  ${CYAN}tmux attach -t $STACK_SESSION${RESET}    — ROS 2 stack"
echo -e "  ${CYAN}tmux attach -t $INF_SESSION${RESET} — inference servers (one pane each)"
echo -e "  ${CYAN}tmux attach -t $AGENTS_SESSION${RESET}   — agents + orchestrator (one pane each)"
echo -e "  ${CYAN}tmux attach -t $HMI_SESSION${RESET}      — HMI"
echo ""
echo -e "  Stop everything:  ${YELLOW}pixi run kill${RESET}"
echo ""

# When run as a container's PID 1 (AMM_KEEP_ALIVE=1), don't return: exiting lets
# the container stop and take the tmux sessions with it. Locally the var is unset
# and the script returns, leaving the sessions in the background.
# With a TTY (docker compose run) attach to tmux so PID 1 is a live client you can
# debug in — prefix+s switches between all sessions, prefix+d detaches and stops
# the demo. Without a TTY (detached compose up / CI) attach would exit instantly,
# so just block until the HMI session goes away.
if [ -n "${AMM_KEEP_ALIVE:-}" ]; then
    if [ -t 0 ]; then
        log "Attaching to tmux — prefix+s to switch sessions, prefix+d detaches (stops the demo)."
        exec tmux attach -t "$HMI_SESSION"
    fi
    log "AMM_KEEP_ALIVE set — holding until the HMI session exits (Ctrl-C / 'pixi run kill' to stop)."
    while tmux has-session -t "$HMI_SESSION" 2>/dev/null; do sleep 5; done
    warn "HMI session gone — exiting."
fi
