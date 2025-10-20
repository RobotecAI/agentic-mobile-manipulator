# Embodied AI for Autonomous Warehouse Robotics

<div align="center">

![Small warehouse featuring Robotnik Kairos](docs/images/demo_comp.jpg)
![Static Badge](https://img.shields.io/badge/AgenticAI-darkred)
![Static Badge](https://img.shields.io/badge/EmbodiedAI-black)
![Static Badge](https://img.shields.io/badge/LLM-darkred)
![Static Badge](https://img.shields.io/badge/VLM-black)
![Static Badge](https://img.shields.io/badge/Local-darkred)

<p align="center">
  <em>End-to-end local inference for embodied agentic AI in a ROS 2 simulation environment.</em>
</p>

[![License](https://img.shields.io/badge/License-Apache_2.0-orange.svg)](https://opensource.org/licenses/Apache-2.0)
![Static Badge](https://img.shields.io/badge/Ubuntu-24.04-orange)
![Static Badge](https://img.shields.io/badge/Python-3.12-orange)
![Static Badge](https://img.shields.io/badge/ROS2-jazzy-orange)

</div>

## About the demo

The demonstration features a fully autonomous warehouse robot capable of perception, reasoning, and natural language understanding. It performs warehouse tasks based on human commands, detects anomalies such as spills or blocked paths, and responds appropriately to maintain safety and efficiency.

The demo illustrates the concept of physical intelligence, where robotics and Agentic AI combine to create adaptable, context-aware systems that can operate reliably in complex industrial settings.

## Architecture & Technology

- Hardware platform: **AMD Ryzen™ AI** processor hosting robotics stack and embodied agentic AI multi-agent system
- Model stack: [**Liquid AI's LFM2-VL**](https://www.liquid.ai/) (Vision-Language Model) optimized for AMD hardware
- Local LLM (gpt-oss-20b) for planning, instruction parsing, and dialogue
- Robot platform: Mobile manipulator (Robotnik Kairos) in ROS 2 simulated warehouse environment
- Simulation setup: Hardware-in-the-loop mirrors real-world deployment for safe testing
- Benefits: On-device reasoning, low latency, privacy, and seamless simulation-to-hardware transition

## Showcase

The demo is showcased at ROSCon 2025 in Singapore, presented jointly by Robotec.ai, AMD, and Liquid AI. Visit the AMD booth (17/18) to experience real-time reasoning, task execution, and human-in-the-loop control through the industrial tablet interface.

## Documentation

- [Demo overview](./docs/demo.md)
- [Setup instructions](./docs/setup.md)
- [Running instructions](./docs/running.md)

## Contributing

Contributions are welcome! Please open an issue to discuss proposed changes or submit a pull request directly. For larger feature work, share your plan first so we can align on design and interfaces.

## License

This project is licensed under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).

## Contact

For questions about the demo or collaboration opportunities, please open an issue in this repository.
