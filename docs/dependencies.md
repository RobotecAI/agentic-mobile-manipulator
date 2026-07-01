# Project dependencies

## O3DE

| Repository URL                        |
| ------------------------------------- |
| https://github.com/RobotecAI/o3de.git |

## O3DE gems

| Gem Name                 | Repository URL                                            |
| ------------------------ | --------------------------------------------------------- |
| o3de-extras              | https://github.com/robotecai/o3de-extras.git              |
| o3de-humanworker-gem     | https://github.com/RobotecAI/o3de-humanworker-gem.git     |
| o3de-ur-robots-gem       | https://github.com/RobotecAI/o3de-ur-robots-gem.git       |
| robotec-o3de-tools       | https://github.com/RobotecAI/robotec-o3de-tools.git       |
| robotec-warehouse-assets | https://github.com/RobotecAI/robotec-warehouse-assets.git |
| robotec-generic-assets   | https://github.com/RobotecAI/robotec-generic-assets.git   |

## ROS 2

| Package Name                      | Repository URL                                                           |
| --------------------------------- | ------------------------------------------------------------------------ |
| rai_interfaces                    | https://github.com/RobotecAI/rai_interfaces.git                          |
| Universal_Robots_ROS2_Description | https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git |
| control_msgs                      | https://github.com/ros-controls/control_msgs.git                         |
| control_toolbox                   | https://github.com/ros-controls/control_toolbox.git                      |
| kinematics_interface              | https://github.com/ros-controls/kinematics_interface.git                 |
| moveit2                           | https://github.com/moveit/moveit2.git                                    |
| moveit_msgs                       | https://github.com/moveit/moveit_msgs.git                                |
| realtime_tools                    | https://github.com/ros-controls/realtime_tools.git                       |
| robotnik_common                   | https://github.com/RobotnikAutomation/robotnik_common.git                |
| robotnik_description              | https://github.com/RobotnikAutomation/robotnik_description.git           |
| robotnik_sensors                  | https://github.com/RobotnikAutomation/robotnik_sensors.git               |
| ros2_control                      | https://github.com/ros-controls/ros2_control.git                         |
| ros2_controllers                  | https://github.com/ros-controls/ros2_controllers                         |
| srdfdom                           | https://github.com/moveit/srdfdom.git                                    |
| simulation_interfaces             | https://github.com/ros-simulation/simulation_interfaces.git              |

## Python

| Package Name | Repository URL                                            |
| ------------ | --------------------------------------------------------- |
| rai-core     | https://github.com/RobotecAI/rai.git                      |
| rai-whoami   | https://github.com/RobotecAI/rai/tree/main/src/rai_whoami |

## Inference

| Inference Engine | Backend          | Repository URL                              |
| ---------------- | ---------------- | ------------------------------------------- |
| llama.cpp        | GPU (Vulkan)/CPU | https://github.com/ggml-org/llama.cpp.git   |
| FastFlowLM       | AMD Ryzen AI NPU | https://github.com/RobotecAI/FastFlowLM.git |

## Models

`config.toml` is the single source of truth for which models are served, on which
backend, and from which weights. The endpoints it defines today:

| Model name           | Type      | Backend          | Source                                           |
| -------------------- | --------- | ---------------- | ------------------------------------------------ |
| gpt-oss-20b          | LLM       | GPU (llama.cpp)  | https://huggingface.co/openai/gpt-oss-20b        |
| LFM2-VL-3B           | VLM       | GPU (llama.cpp)  | https://huggingface.co/LiquidAI/LFM2-VL-3B-GGUF  |
| gemma3:4b            | VLM       | NPU (FastFlowLM) | https://huggingface.co/google/gemma-3-4b-it      |
| Qwen3-Embedding-0.6B | Embedding | GPU (llama.cpp)  | https://huggingface.co/Qwen/Qwen3-Embedding-0.6B |
| Qwen3-Reranker-0.6B  | Reranker  | GPU (llama.cpp)  | https://huggingface.co/Qwen/Qwen3-Reranker-0.6B  |

LFM2-VL-3B serves the inspection, general, megamind, and condition agents; gemma3:4b
serves the safety agent on the NPU.
