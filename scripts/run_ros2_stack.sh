(
  ros2 launch robotec_kairos_ur10 robotec_launch.py &
  uv run python rai_app/agents/nav2_agent.py $1 &
  uv run python rai_app/agents/moveit2_agent.py $1 &
  wait
)
