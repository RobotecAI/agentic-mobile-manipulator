#!/usr/bin/env bash
set -e 

uv sync
exec uv run python rai_app/agent.py "$@" 

