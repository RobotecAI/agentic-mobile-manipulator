# Setup HMI Environment

<p align="center">
  <img src="images/hmi.png" alt="HMI graphical interface" width="50%"/>
</p>

This repository is compatible with the following system:

- System: Ubuntu 24.04
- ROS 2: Jazzy with development tools installed [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#install-development-tools-optional)
- Python: 3.12

## Building the GUI

```shell
cd ${DEMO_ROOT}/ros2_ws/
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## Running the GUI

```shell
ros2 launch mobile_manipulator_hmi hmi_launch.py

```

## ROS2 interfaces provided by the GUI

### 📨 Subscriptions

| **Interface** | **Message Type**                | **Topic**                          | **Description**                                                              |
| ------------- | ------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------- |
| Subscription  | `sensor_msgs/msg/Image`         | `/rgbd_camera/camera_image_color`  | Receives image data from a camera or visual sensor.                          |
| Subscription  | `sensor_msgs/msg/Image`         | `/wrist_camera/camera_image_color` | Receives image data from a top-mounted camera or secondary visual sensor.    |
| Subscription  | `nav_msgs/msg/OccupancyGrid`    | `/global_costmap/static_layer`     | Subscribes to the global map used for navigation and planning.               |
| Subscription  | `nav_msgs/msg/Path`             | `/plan`                            | Receives the computed navigation path from the planner.                      |
| Subscription  | `std_msgs/msg/Header`           | `/orchestrator/heartbeat`          | Receives heartbeat messages from the orchestrator to monitor its status.     |
| Subscription  | `rcl_interfaces/msg/Log`        | `/rosout`                          | Receives log messages for runtime diagnostics and filtering.                 |
| Subscription  | `demo_msgs/msg/Utilization`     | `/utilization`                     | Receives system or resource utilization metrics.                             |
| Subscription  | `demo_msgs/msg/VlmDescription`  | `/vlm_topic`                       | Receives VLM (Vision-Language Model) description messages.                   |
| Subscription  | `rai_interfaces/msg/HRIMessage` | `/agent/current_action`            | Receives Agents description of current action.                               |
| Subscription  | `std_msgs/msg/String`           | `/agent/past_steps`                | Receives Agents list of past actions. string('\["step1", "step2"\]')         |
| Subscription  | `std_msgs/msg/String`           | `/orchestrator/current_task`       | Receives Agents description of current task.                                 |
| Subscription  | `std_msgs/msg/String`           | `/orchestrator/tasks_queue`        | Receives Agents list of task queue. string('\["task1", "task2"\]')           |
| Subscription  | `std_msgs/msg/String`           | `/orchestrator/paused_tasks`       | Receives Agents list of paused tasks. Format: string('\["task1", "task2"\]') |

---

### 📤 Publishers

| **Interface** | **Message Type**                | **Topic**         | **Description**                                                         |
| ------------- | ------------------------------- | ----------------- | ----------------------------------------------------------------------- |
| Publisher     | `geometry_msgs/msg/PoseStamped` | `/goal_pose`      | Publishes navigation goals for the robot.                               |
| Publisher     | `geometry_msgs/msg/Twist`       | `/cmd_vel`        | Publishes velocity commands for robot motion control.                   |
| Publisher     | `std_msgs/msg/String`           | `/user_tasks`     | Publishes user prompts for interactive task selection or notifications. |
| Publisher     | `std_msgs/msg/String`           | `/emergency_stop` | Publishes emergency stop commands to halt robot operations.             |

---

### 🧠 Services

| **Interface** | **Service Type**       | **Service Name**       | **Description**                                                      |
| ------------- | ---------------------- | ---------------------- | -------------------------------------------------------------------- |
| Client        | `std_srvs/srv/Trigger` | `/restart`             | Invokes a restart or reset of the orchestrator or system components. |
| Client        | `std_srvs/srv/Trigger` | `/rai/scene/housekeep` | Setups the housekeeping task scene.                                  |
| Client        | `std_srvs/srv/Trigger` | `/rai/scene/anomalies` | Setups the anomalies detection scene.                                |
| Client        | `std_srvs/srv/Trigger` | `/rai/scene/standard`  | Setups the standard scene.                                           |
| Client        | `std_srvs/srv/Trigger` | `/rai/scene/cleanup`   | Cleans the scene from all entities.                                  |
