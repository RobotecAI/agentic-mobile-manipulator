#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()    { echo -e "  ${GREEN}●${RESET} $*"; }
warn()   { echo -e "  ${YELLOW}!${RESET} $*"; }
err()    { echo -e "  ${RED}✗${RESET} $*" >&2; exit 1; }
ok()     { echo -e "  ${GREEN}✓${RESET} $*"; }
section(){ echo -e "\n${BOLD}${CYAN}$*${RESET}"; }

# ── Guard ─────────────────────────────────────────────────────────────────────

for s in simulation inference agent; do
    if tmux has-session -t "$s" 2>/dev/null; then
        warn "Session '$s' already exists."
        warn "Run 'pixi run demo-stop' first, or attach with: tmux attach -t $s"
        exit 1
    fi
done

trap 'echo; warn "Interrupted. Run: pixi run demo-stop"' INT TERM

# ── 1. Simulation ─────────────────────────────────────────────────────────────

section "Starting simulation..."

tmux new-session -d -s simulation -x 220 -y 50
tmux rename-window -t simulation:0 "sim+ros2"
tmux split-window -v -t simulation:0.0

tmux send-keys -t simulation:0.0 "cd $DEMO_ROOT && pixi run sim" Enter
log "O3DE launched  (simulation — top pane)"

echo -ne "  ${YELLOW}○${RESET} Waiting for /clock"
elapsed=0
while ! ros2 topic list 2>/dev/null | grep -q "^/clock$"; do
    sleep 2; elapsed=$((elapsed + 2)); echo -n "."
    [ $elapsed -ge 120 ] && echo && err "Timed out waiting for /clock (120 s)"
done
echo -e " ${GREEN}✓${RESET}"

# ── 2. ROS 2 Stack ────────────────────────────────────────────────────────────

section "Starting ROS 2 stack..."

tmux send-keys -t simulation:0.1 "cd $DEMO_ROOT && pixi run ros2" Enter
ok "ROS 2 stack launched  (simulation — bottom pane)"

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

echo -ne "  ${YELLOW}○${RESET} Waiting for inference servers"
elapsed=0
while true; do
    all_up=true
    for port in 8080 8081 8082 8083; do
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 \
               "http://localhost:$port/health" 2>/dev/null)
        [ "$code" != "200" ] && all_up=false && break
    done
    if $all_up; then echo -e " ${GREEN}✓${RESET}"; break; fi
    sleep 5; elapsed=$((elapsed + 5)); echo -n "."
    if [ $elapsed -ge 600 ]; then
        echo
        warn "Not all inference servers ready after 600 s — continuing anyway"
        break
    fi
done

# ── 4. Orchestrator ───────────────────────────────────────────────────────────

section "Starting orchestrator..."

tmux new-session -d -s agent -x 220 -y 50
tmux rename-window -t agent:0 "orchestrator"
tmux send-keys -t agent:0 "cd $DEMO_ROOT && pixi run orchestrator" Enter
ok "Orchestrator launched  (agent)"

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}=== Demo running ===${RESET}"
echo ""
echo -e "  ${CYAN}tmux attach -t simulation${RESET}   — O3DE sim (top) + ROS 2 stack (bottom)"
echo -e "  ${CYAN}tmux attach -t inference${RESET}    — 4 inference servers (2×2 grid)"
echo -e "  ${CYAN}tmux attach -t agent${RESET}        — orchestrator"
echo ""
echo -e "  Stop everything:  ${YELLOW}pixi run demo-stop${RESET}"
echo ""
