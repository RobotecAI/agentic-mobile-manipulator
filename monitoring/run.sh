#!/bin/bash

sim=$1
if [ -z "$sim" ]; then
    echo "Usage: $0 [navigation|manipulation]"
    exit 1
fi

SCRIPT_NAME="main.py"

pkill -f "ollama"

python3 "$SCRIPT_NAME" --run-time 200 --model-vl "qwen2.5vl:3b" --model-llm "qwen2.5:7b"  --sim "$sim"

pkill -f "ollama"

python3 "$SCRIPT_NAME" --run-time 450 --model-vl "qwen2.5vl:7b" --model-llm "qwen2.5:14b" --sim "$sim"

pkill -f "ollama"

python3 "$SCRIPT_NAME" --run-time 600 --model-vl "qwen2.5vl:7b" --model-llm "qwen2.5:32b" --sim "$sim"

