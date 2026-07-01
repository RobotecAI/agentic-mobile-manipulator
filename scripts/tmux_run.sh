#!/usr/bin/env bash
# Launch a command in its own project-prefixed tmux session (so `pixi run kill`
# can stop it). Used by the sim and stack tasks.
#   tmux_run.sh SESSION CMD...
# CMD is a `pixi run <task>` so the pane gets the activated runtime — a fresh
# tmux pane does not inherit this shell's environment.
set -euo pipefail
session="$1"; shift

if ! command -v tmux >/dev/null; then
  echo "tmux is required; run the foreground task instead (e.g. \`pixi run sim-fg\`)" >&2
  exit 1
fi

if tmux has-session -t "$session" 2>/dev/null; then
  echo "Session '$session' already exists."
else
  tmux new-session -d -s "$session" -x 220 -y 50
  tmux send-keys -t "$session" "$*" Enter
fi

# Leave the session detached when nested in tmux or when a caller (demo.sh)
# only wants it started, not attached.
[ -n "${TMUX:-}${AMM_NO_ATTACH:-}" ] && exit 0
exec tmux attach-session -t "$session"
