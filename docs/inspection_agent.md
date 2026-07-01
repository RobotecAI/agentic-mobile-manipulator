# Inspection Agent Documentation

## Overview

The Inspection Agent is a Vision-Language-Model (VLM) based system designed to detect anomalies in warehouse environments.
It continuously monitors camera feed to identify objects that are not probable in a typical warehouse setting.

![Inspection Agent Overview](images/inspection_agent.png)

## Usage

```bash
pixi run inspection-agent
```

This wraps `uv run python rai_app/agents/inspection_agent.py`, so you can run that directly if you need to pass extra flags.

## Architecture

### Core Components

#### 1. VlmWarehouseInspector

The main agent class that orchestrates the inspection process.

**Key Responsibilities:**

- Manages camera image processing
- Coordinates VLM analysis
- Handles anomaly reporting
- Manages ROS2 communication

#### 2. Perception bypass using Ground Truth information from Simulation

- Provides spatial context for anomaly detection by returning the pose of closest anomaly in the viewport
- Is triggered when VLM detects the anomaly in the image

## Configuration

### Command Line Arguments

| Argument               | Default                            | Description                             |
| ---------------------- | ---------------------------------- | --------------------------------------- |
| `--slots-file`         | `scripts/resources/slots.csv`      | Path to warehouse slots configuration   |
| `--spawnables-file`    | `scripts/resources/spawnables.csv` | Path to spawnable objects configuration |
| `--camera-topic`       | `/rgbd_camera/camera_image_color`  | ROS2 camera topic                       |
| `--ego-source-frame`   | `egobase_footprint`                | Robot base frame                        |
| `--ego-target-frame`   | `odom`                             | Target coordinate frame                 |
| `--anomaly-images-dir` | `./anomaly_images`                 | Directory to save anomaly images        |
| `--anomalies-topic`    | `/inspection_result`               | ROS2 topic for anomaly reports          |
| `--n-seconds`          | `5`                                | Minimum interval between VLM processing |

## ROS2 Integration

### Input Topics

| Topic                             | Message Type             | Description            |
| --------------------------------- | ------------------------ | ---------------------- |
| `/rgbd_camera/camera_image_color` | `sensor_msgs/msg/Image`  | Camera image feed      |
| `/tf`                             | `tf2_msgs/msg/TFMessage` | Robot pose information |

### Output Topics

| Topic                | Message Type                         | Description                                              |
| -------------------- | ------------------------------------ | -------------------------------------------------------- |
| `/inspection_result` | `robotec_kairos_ur10/msg/Anomaly`    | Anomaly detection results                                |
| `/marker`            | `visualization_msgs/msg/MarkerArray` | Optional debug markers for RViz2 enabled using `--debug` |
| `/vlm_topic`         | `demo_msgs/msg/VlmDescription`       | Visual descriptions for HMI                              |

### Message Types

#### Anomaly Message

```python
class Anomaly:
    pose: geometry_msgs.msg.Pose          # Object location
    obstacle_type: str                    # "box", "trash", or "other"
    anomaly_description: str              # Human-readable description
    filename: str                         # Saved image filename (optional)
```

#### AnomalyDescription (VLM Output)

The VLM returns this structured output. There is no separate detected flag: an
`obstacle_type` of `"nothing"` means the VLM saw no anomaly.

```python
class AnomalyDescription(BaseModel):
    obstacle_type: Literal["box", "trash", "nothing", "other"]  # Object classification
    anomaly_description: str              # Description, max 20 chars, empty if no obstacle
```

## Troubleshooting

### Common Issues

1. **Camera Topic Not Found**

   - Ensure camera is publishing to the correct topic
   - Check topic name with `ros2 topic list`

2. **VLM Processing Failures**
   - Verify VLM server is running and accessible
   - Check if model supports image processing
   - Review VLM server logs for errors

### Debug Mode

Enable debug mode to see additional logging and visualization:

```python
inspector = VlmWarehouseInspector(debug=True, ...)
```
