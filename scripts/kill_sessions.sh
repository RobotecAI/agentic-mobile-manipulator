#!/usr/bin/env bash
# Kill every tmux session this project starts. All session names share the
# `agentic-mobile-manipulator` prefix (see demo.sh, run_agents.sh, serve.py).
killed=false
while read -r s; do
    [ -z "$s" ] && continue
    tmux kill-session -t "$s" 2>/dev/null && echo "  killed '$s'" && killed=true
done < <(tmux ls -F '#{session_name}' 2>/dev/null | grep '^agentic-mobile-manipulator')
$killed || echo "  no agentic-mobile-manipulator sessions running"
