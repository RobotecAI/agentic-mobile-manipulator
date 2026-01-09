#!/usr/bin/env bash
set -e

source /root/MobileManipulatorDemo/ros2_ws/install/setup.bash

exec uv run python rai_app/agents/agent_orchestrator.py
