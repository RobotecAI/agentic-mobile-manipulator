# Setup HMI Environment

<p align="center">
  <img src="images/hmi.png" alt="HMI graphical interface" width="50%"/>
</p>

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy, provided by pixi via RoboStack (no separate ROS 2 install needed)
- Python: 3.12

## Building the GUI

```shell
pixi run -e hmi setup
```

This clones the ROS 2 workspace, builds it with colcon, and syncs the Python
dependencies. pixi activates the ROS 2 environment for you, so there's no separate
ROS 2 install or manual sourcing to do.

## Running the GUI

```shell
pixi run -e hmi hmi
```

This launches the HMI in its own tmux session. To run it in the foreground
instead, use `pixi run -e hmi hmi-fg`, which calls
`ros2 launch mobile_manipulator_hmi hmi_launch.py` directly.

Set `HMI_WINDOWED=1` to start in a window instead of full screen; F11 toggles.

## What the HMI shows

The HMI is a Qt Quick (QML) app: `RosBridge` (C++) owns the ROS 2 node and exposes
state to the QML pages under `qml/`. It has four pages:

- **Mission**: task input, cameras, map, current task with its steps, the queue, and
  the live agent stream.
- **Agents**: which agent is doing what, and a timeline of the current task with the
  full content of each message, tool call and finding.
- **Simulation**: scene recipes, task builders (sort returns, housekeeping by rack,
  shipments) and manual driving.
- **System**: CPU/GPU/NPU/RAM, agent heartbeats, inference endpoint health (read from
  `config.toml`, polled over HTTP) and `/rosout` logs.

## ROS 2 interfaces

### Subscriptions

| Message type                    | Topic                              | Use                                                                                                 |
| ------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| `std_msgs/msg/String`           | `/agent/events`                    | Agent event stream, one JSON object per message (below).                                            |
| `rai_interfaces/msg/HRIMessage` | `/agent/current_action`            | Older stream, used only until the first `/agent/events` message.                                    |
| `std_msgs/msg/String`           | `/agent/past_steps`                | Steps done in the current task.                                                                     |
| `std_msgs/msg/String`           | `/orchestrator/current_task`       | Current task prompt.                                                                                |
| `std_msgs/msg/String`           | `/orchestrator/tasks_queue`        | Queued task prompts, `\|`-separated.                                                                |
| `std_msgs/msg/Bool`             | `/orchestrator/estop`              | Whether the orchestrator is emergency-stopped.                                                      |
| `std_msgs/msg/Header`           | `/orchestrator/heartbeat`          | Orchestrator liveness.                                                                              |
| `std_msgs/msg/Header`           | `/agents/heartbeat`                | Every agent process, `frame_id` = `orchestrator`, `nav2`, `moveit2`, `scene`, `inspection`, `safety`. |
| `demo_msgs/msg/VlmDescription`  | `/vlm_topic`                       | Inspection and safety findings with their image.                                                    |
| `demo_msgs/msg/Utilization`     | `/utilization`                     | CPU/GPU/NPU/RAM and Nav2/MoveIt2 state (from `utilization_node`).                                   |
| `sensor_msgs/msg/Image`         | `/rgbd_camera/camera_image_color`  | Base camera.                                                                                        |
| `sensor_msgs/msg/Image`         | `/wrist_camera/camera_image_color` | Wrist camera.                                                                                       |
| `sensor_msgs/msg/Image`         | `/camera_image_color`              | Top camera.                                                                                         |
| `nav_msgs/msg/OccupancyGrid`    | `/global_costmap/static_layer`     | Map.                                                                                                |
| `nav_msgs/msg/Path`             | `/plan`                            | Planned path.                                                                                       |
| `rosgraph_msgs/msg/Clock`       | `/clock`                           | Simulation time.                                                                                    |
| `rcl_interfaces/msg/Log`        | `/rosout`                          | Logs.                                                                                               |

The robot pose comes from TF (`map` → `egobase_link`).

### `/agent/events`

Each message is a JSON object with `type` and `t` (Unix time), published by
`rai_app/agents/callbacks.py` and the orchestrator:

| `type`                 | Fields                                  |
| ---------------------- | --------------------------------------- |
| `task_start`           | `task`                                  |
| `task_end`             | `task`, `status` (`done`, `failed`, `aborted`) |
| `text`, `thinking`     | `node`, `run_id`, `chunk` (streamed)    |
| `tool_start`           | `node`, `run_id`, `tool`, `args`        |
| `tool_end`             | `run_id`, `tool`, `output`, `status` (`ok`, `error`) |
| `llm_end`              | `node`, `tokens_in`, `tokens_out`       |
| `steps`                | `steps` (list of done steps)            |

`node` is the agent graph node: `megamind` (orchestrator), `housekeep`,
`package_movement`, `image_analysis`.

### Publishers

| Message type                    | Topic                | Use                                                                 |
| ------------------------------- | -------------------- | ------------------------------------------------------------------- |
| `std_msgs/msg/String`           | `/user_tasks`        | Tasks for the orchestrator.                                         |
| `std_msgs/msg/Empty`            | `/emergency_stop`    | E-STOP: the orchestrator aborts the task and clears the queue, Nav2 pauses. |
| `std_msgs/msg/Empty`            | `/emergency_release` | Release: the orchestrator accepts tasks again, Nav2 resumes.        |
| `geometry_msgs/msg/Twist`       | `/cmd_vel`           | Manual driving.                                                     |
| `geometry_msgs/msg/PoseStamped` | `/goal_pose`         | Navigation goal (double-click on the map).                          |

### Service clients

| Service type           | Service                | Use                                  |
| ---------------------- | ---------------------- | ------------------------------------ |
| `std_srvs/srv/Trigger` | `/rai/scene/standard`  | Standard scene.                      |
| `std_srvs/srv/Trigger` | `/rai/scene/housekeep` | Housekeeping scene.                  |
| `std_srvs/srv/Trigger` | `/rai/scene/anomalies` | Anomalies scene.                     |
| `std_srvs/srv/Trigger` | `/rai/scene/cleanup`   | Reset the simulation, remove objects. |

## Checking the UI without a display

`HMI_SCREENSHOT=<file.png>` saves the window after `HMI_SCREENSHOT_MS` (default 4000)
and quits; `HMI_PAGE=0..3` picks the page. For example:

```shell
HMI_WINDOWED=1 HMI_PAGE=1 HMI_SCREENSHOT=agents.png QT_QUICK_BACKEND=software \
  xvfb-run -a -s "-screen 0 1440x900x24" ros2 run mobile_manipulator_hmi MobileManipulatorHMI
```
