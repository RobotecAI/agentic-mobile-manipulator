#!/usr/bin/env bash
# Start the rai agents + orchestrator (the AI layer driving the ROS 2 stack) in
# a tmux tiled grid, one pane each. Requires the barebones stack
# (`pixi run stack`) and the inference servers to be up. Any extra args
# ($@, e.g. --test-mode) are forwarded to the nav2 and moveit2 agents.
set -euo pipefail

SESSION="agentic-mobile-manipulator-agents"
WINDOW="agents"
EXTRA="${*:-}"

# Each pane re-enters pixi so it gets the activated runtime (a fresh tmux pane
# does not inherit this shell's environment).
PANES=(
  "pixi run nav2-agent ${EXTRA}"
  "pixi run moveit2-agent ${EXTRA}"
  "pixi run scene-agent"
  "pixi run inspection-agent"
  "pixi run safety-agent"
  "pixi run orchestrator"
)

if ! command -v tmux >/dev/null; then
  echo "tmux is required for \`pixi run agents\` (run individual agents instead, e.g. \`pixi run nav2-agent\`)" >&2
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already exists."
else
  tmux new-session -d -s "$SESSION" -n "$WINDOW" -x 220 -y 50
  tmux send-keys -t "$SESSION:$WINDOW" "${PANES[0]}" Enter
  for cmd in "${PANES[@]:1}"; do
    tmux split-window -t "$SESSION:$WINDOW"
    tmux select-layout -t "$SESSION:$WINDOW" tiled
    tmux send-keys -t "$SESSION:$WINDOW" "$cmd" Enter
  done
  tmux select-layout -t "$SESSION:$WINDOW" tiled
fi

# Leave detached when nested in tmux or when a caller (demo.sh) only wants it started.
[ -n "${TMUX:-}${AMM_NO_ATTACH:-}" ] && exit 0
exec tmux attach-session -t "$SESSION"
