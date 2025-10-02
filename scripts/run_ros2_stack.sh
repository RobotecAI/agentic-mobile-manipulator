(
  ros2 launch robotec_kairos_ur10 robotec_launch.py &
  uv run python rai_app/nav2_agent.py &
  uv run python rai_app/moveit2_agent.py &
  wait
)
