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

Most ROS 2 dependencies (MoveIt 2, Nav2, `ros2_control`, `control_msgs`,
`simulation_interfaces`, and the rest) come from the
[RoboStack](https://robostack.github.io) `robostack-jazzy` conda channel and are
installed automatically by pixi — see `[dependencies]` in `pixi.toml`. They are no
longer vcs-imported or built from source.

These packages are built from source (see `ros2_ws.repos`):

| Package Name         | Repository URL                                                 |
| -------------------- | -------------------------------------------------------------- |
| robotnik_common      | https://github.com/RobotnikAutomation/robotnik_common.git      |
| robotnik_description | https://github.com/RobotnikAutomation/robotnik_description.git |
| robotnik_sensors     | https://github.com/RobotnikAutomation/robotnik_sensors.git     |
| rai_interfaces       | https://github.com/RobotecAI/rai_interfaces.git                |

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
