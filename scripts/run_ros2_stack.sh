(
  ros2 launch robotec_kairos_ur10 robotec_launch.py &
  ros2 run mobile_manipulator_hmi utilization_node &
  uv run python rai_app/agents/nav2_agent.py $1 &
  uv run python rai_app/agents/moveit2_agent.py $1 &
  uv run python rai_app/environment/scene_agent.py &
  uv run python rai_app/control/nav_lifecycle_node.py &
  uv run python rai_app/agents/inspection_agent.py 2>&1 | tee inspection_agent.log &
  ./scripts/start_safety_agent.sh 2>&1 | tee safety_agent.log &
  wait
)
