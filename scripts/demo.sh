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

tmux new-session -d -s simulation -x 220 -y 50
tmux rename-window -t simulation:0 "sim+ros2"
tmux split-window -v -t simulation:0.0

tmux send-keys -t simulation:0.0 "cd $DEMO_ROOT && pixi run sim" Enter
log "O3DE launched  (simulation — top pane)"

wait_topic "/clock" 120 || { stop_all; exit 1; }

# ── 2. ROS 2 Stack ────────────────────────────────────────────────────────────

section "Starting ROS 2 stack..."

tmux send-keys -t simulation:0.1 "cd $DEMO_ROOT && pixi run ros2" Enter
log "ROS 2 stack launched  (simulation — bottom pane)"

wait_topic "/joint_states" 60 || { stop_all; exit 1; }

# ── 3. Inference servers ──────────────────────────────────────────────────────

section "Starting inference servers..."

tmux new-session -d -s inference -x 220 -y 50
tmux rename-window -t inference:0 "models"
tmux split-window -h -t inference:0.0
tmux split-window -v -t inference:0.0
tmux split-window -v -t inference:0.2
tmux select-layout -t inference:0 tiled

tmux send-keys -t inference:0.0 "cd $DEMO_ROOT && pixi run serve-llm"       Enter
tmux send-keys -t inference:0.1 "cd $DEMO_ROOT && pixi run serve-embedding"  Enter
tmux send-keys -t inference:0.2 "cd $DEMO_ROOT && pixi run serve-vlm"        Enter
tmux send-keys -t inference:0.3 "cd $DEMO_ROOT && pixi run serve-reranker"   Enter
log "Inference session created  (inference — 2×2 grid)"

check_inference || { stop_all; exit 1; }

# ── 4. Orchestrator ───────────────────────────────────────────────────────────

section "Starting orchestrator..."

tmux new-session -d -s agent -x 220 -y 50
tmux rename-window -t agent:0 "orchestrator"
tmux send-keys -t agent:0 "cd $DEMO_ROOT && pixi run orchestrator" Enter
log "Orchestrator launched  (agent)"

# ── Final health check ────────────────────────────────────────────────────────

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

for port in 8080 8081 8082 8083; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 \
           "http://localhost:$port/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        ok "Inference port $port — OK"
    else
        err "Inference port $port — not responding (HTTP $code)"
        failed=true
    fi
done

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
echo -e "  ${CYAN}tmux attach -t inference${RESET}    — 4 inference servers (2×2 grid)"
echo -e "  ${CYAN}tmux attach -t agent${RESET}        — orchestrator"
echo ""
echo -e "  Stop everything:  ${YELLOW}pixi run demo-stop${RESET}"
echo ""
