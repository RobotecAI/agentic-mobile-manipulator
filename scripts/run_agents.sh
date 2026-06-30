#!/usr/bin/env bash
# Start the rai agents (the AI layer driving the ROS 2 stack). Requires the
# barebones stack (`pixi run ros2`) and the inference servers to be up. The
# orchestrator is launched separately (`pixi run orchestrator`).
(
  uv run python rai_app/agents/nav2_agent.py $1 &
  uv run python rai_app/agents/moveit2_agent.py $1 &
  uv run python rai_app/environment/scene_agent.py &
  uv run python rai_app/agents/inspection_agent.py &
  ./scripts/start_safety_agent.sh &
  wait
)
