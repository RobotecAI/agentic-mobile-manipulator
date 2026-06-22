#!/usr/bin/env bash
# Launch the mock ROS 2 backend for the Web HMI: rosbridge (+ optional
# web_video_server) + the mock data publisher. Ctrl-C stops everything.
#
#   ./web_hmi/tools/run_mock_stack.sh
#
# Then, in another terminal:  cd web_hmi && npm run dev   ->  http://localhost:5173
# NOTE: no `-u` — ROS 2 setup scripts reference unbound vars (AMENT_TRACE_SETUP_FILES…)
set -eo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
# demo_msgs (built in the ROS workspace); rai_interfaces ships with /opt/ros/jazzy
if [ -f "$REPO/ros2_ws/install/demo_msgs/share/demo_msgs/local_setup.bash" ]; then
  # shellcheck disable=SC1091
  source "$REPO/ros2_ws/install/demo_msgs/share/demo_msgs/local_setup.bash"
else
  echo "!! demo_msgs not built. Run: cd ros2_ws && colcon build --packages-select demo_msgs"
  exit 1
fi

pids=()
cleanup() { echo; echo "stopping…"; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup INT TERM EXIT

echo ">> rosbridge_server  (ws://localhost:9090)"
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
pids+=($!)

if ros2 pkg prefix web_video_server >/dev/null 2>&1; then
  echo ">> web_video_server  (http://localhost:8080)"
  ros2 run web_video_server web_video_server &
  pids+=($!)
else
  echo "-- web_video_server not installed (camera tiles will show 'offline')"
fi

sleep 2
echo ">> mock data publisher"
python3 "$REPO/web_hmi/tools/mock_ros_publisher.py" &
pids+=($!)

echo
echo "Mock stack up. Start the UI:  cd web_hmi && npm run dev   ->  http://localhost:5173"
echo "Press Ctrl-C to stop."
wait
