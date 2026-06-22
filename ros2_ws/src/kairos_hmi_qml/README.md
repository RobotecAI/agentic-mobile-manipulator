# kairos_hmi_qml

A **Qt Quick (QML)** Human-Machine-Interface for the Robotnik Kairos+ — a
native, GPU-accelerated port of the web HMI's "Kairos Command" design
(glassmorphism, gradient accents, glow, radial gauges, animated nav).

It is a normal ROS 2 node: a C++/`rclcpp` backend (`RosBridge`) subscribes to
the live topics, serves the scenario/restart services, renders camera frames and
the occupancy map to `QImage`s, and exposes everything to QML as properties,
signals and invokable commands. No rosbridge/web_video_server needed — it speaks
ROS 2 directly.

## Build

```bash
cd ros2_ws
colcon build --packages-select demo_msgs kairos_hmi_qml
source install/setup.bash
```

Requires Qt 5 Quick + Controls 2 + GraphicalEffects:

```bash
sudo apt-get install -y qtdeclarative5-dev qml-module-qtquick-controls2 \
    qml-module-qtquick-layouts qml-module-qtgraphicaleffects qml-module-qtquick-window2
```

## Run

```bash
ros2 run kairos_hmi_qml kairos_hmi_qml
```

`KAIROS_TAB=0|1|2` selects the initial view (Mission / Control / Telemetry).

### With mock data

The same mock publisher used by the web HMI drives this app (it only needs the
ROS topics — not rosbridge):

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
python3 web_hmi/tools/mock_ros_publisher.py
```

## ROS interfaces

Mirrors the native Widgets HMI. **Subscribes**: `/utilization`,
`/orchestrator/{heartbeat,current_task,tasks_queue}`, `/agent/{current_action,past_steps}`,
`/vlm_topic`, `/rosout`, `/global_costmap/static_layer`, `/plan`,
`/rgbd_camera/camera_image_color`, `/wrist_camera/camera_image_color`,
`/camera_image_color`, and TF (`map`→`egobase_link`). **Publishes**:
`/user_tasks`, `/cmd_vel`, `/emergency_stop`. **Calls** (`std_srvs/Trigger`):
`/restart`, `/rai/scene/{standard,housekeep,anomalies,cleanup}`.

## Layout

- `src/RosBridge.{h,cpp}` — ROS 2 ↔ QML bridge (spun on the GUI thread).
- `src/CameraImageProvider.h` — serves camera/map frames to QML `Image`.
- `qml/Main.qml` — window, ambient background, header, segmented nav, view stack.
- `qml/components/` — glass panels, radial gauge, sparkline, status orb, buttons, tiles.
- `qml/views/` — Mission, Control, Telemetry.
