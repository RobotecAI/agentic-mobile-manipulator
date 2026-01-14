# Agentic Mobile Manipulator Demo

_Physical AI for Warehouse Robotics_

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

It is the first demo of agentic embodied AI running fully on board of a portable compute platform (**AMD Ryzen™ AI**).
The demo illustrates agentic approach to physical intelligence, where agents orchestrate a typical robot manipulation and navigation stack. Compared to dedicated robot foundation models, this approach retains steate of the art robotic software in low-level-control, and is low cost due to use of off-shelf general models and fine-tuning with simulation.

See more in the demo video:

https://github.com/user-attachments/assets/4468084b-e950-4af1-ad41-4a17dedbd1e6

Backup video link: https://vimeo.com/1138627688/dbfa881a27

### Architecture & Technology Overview

- Software stack: ROS 2, O3DE and [RAI](https://github.com/RobotecAI/rai)
- Hardware platform: **AMD Ryzen™ AI** processor hosting robotics stack and embodied agentic AI multi-agent system
- Model stack: [**Liquid AI's LFM2-VL**](https://www.liquid.ai/) (Vision-Language Model) optimized for AMD hardware
- Local LLM (gpt-oss-20b) for planning, instruction parsing, and dialogue
- Robot platform: Mobile manipulator (Robotnik Kairos) in ROS 2 simulated warehouse environment
- Simulation setup: Hardware-in-the-loop mirrors real-world deployment for safe testing
- Benefits: On-device reasoning, low latency, privacy, and seamless simulation-to-hardware transition

## Running the Demo

The original demo presented at ROSCon 2025 utilized a specific set of models, including custom fine-tunes. To facilitate easy setup, this repository is configured to use cloud vendors as a plug-and-play alternative.

- Quickstart: [Docker Compose](./docs/quickstart.md)
- Detailed setup: [Setup Guide](./docs/setup.md)
- More details: [Table of Contents](./docs/toc.md)

## Acknowledgment

This project was made possible thanks to AMD, who supported the development and joint presentation of the demo. It was showcased by Robotec.ai, AMD, and Liquid AI at ROSCon 2025 in Singapore.

## License

This project is licensed under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).

## Contributing

Contributions are welcome! Please open an issue to discuss proposed changes or submit a pull request directly.

---

Developed by: <a href="https://robotec.ai/">Robotec.ai</a>

<img src="https://robotec.ai/robotec.svg" alt="Robotec.ai Logo" width="200">
