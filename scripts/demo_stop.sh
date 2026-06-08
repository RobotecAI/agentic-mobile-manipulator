#!/usr/bin/env bash
for s in simulation inference agent; do
    tmux kill-session -t "$s" 2>/dev/null && echo "  killed '$s'" || true
done
