#!/usr/bin/env bash
# Barebones ROS 2 stack: robot bringup + supporting nodes. No agents — start
# those with `pixi run agents` (and `pixi run orchestrator`) once this is up.
(
  ros2 launch robotec_kairos_ur10 robotec_launch.py &
  ros2 run mobile_manipulator_hmi utilization_node &
  uv run python rai_app/control/nav_lifecycle_node.py &
  wait
)
