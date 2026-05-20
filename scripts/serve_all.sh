#!/usr/bin/env bash
set -e

SESSION="llm-servers"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already exists. Attaching..."
    tmux attach-session -t "$SESSION"
    exit 0
fi

tmux new-session -d -s "$SESSION" -n inference -x 220 -y 50

INF_TOP_LEFT=$(tmux display-message -p -t "$SESSION:inference" "#{pane_id}")
INF_TOP_RIGHT=$(tmux split-window -h -P -F "#{pane_id}" -t "$INF_TOP_LEFT")
INF_BOTTOM_LEFT=$(tmux split-window -v -P -F "#{pane_id}" -t "$INF_TOP_LEFT")
INF_BOTTOM_RIGHT=$(tmux split-window -v -P -F "#{pane_id}" -t "$INF_TOP_RIGHT")

tmux send-keys -t "$INF_TOP_LEFT" "pixi run serve-llm" Enter
tmux send-keys -t "$INF_TOP_RIGHT" "pixi run serve-embedding" Enter
tmux send-keys -t "$INF_BOTTOM_LEFT" "pixi run serve-vlm" Enter
tmux send-keys -t "$INF_BOTTOM_RIGHT" "pixi run serve-reranker" Enter

tmux select-layout -t "$SESSION:inference" tiled

tmux attach-session -t "$SESSION"
