#!/usr/bin/env bash
set -e

SESSION="llm-servers"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already exists. Attaching..."
    tmux attach-session -t "$SESSION"
    exit 0
fi

tmux new-session -d -s "$SESSION" -x 220 -y 50

tmux rename-window -t "$SESSION:0" "inference"

# 2x2 grid: split into 4 panes
tmux split-window -h -t "$SESSION:0"
tmux split-window -v -t "$SESSION:0.0"
tmux split-window -v -t "$SESSION:0.2"

tmux send-keys -t "$SESSION:0.0" "pixi run serve-llm" Enter
tmux send-keys -t "$SESSION:0.1" "pixi run serve-embedding" Enter
tmux send-keys -t "$SESSION:0.2" "pixi run serve-vlm" Enter
tmux send-keys -t "$SESSION:0.3" "pixi run serve-reranker" Enter

tmux select-layout -t "$SESSION:0" tiled

tmux attach-session -t "$SESSION"
