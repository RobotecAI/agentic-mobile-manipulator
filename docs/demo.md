# Demo content

The demo features a Robotnik Kairos+ mobile manipulator operating in a small warehouse facility. The system runs on a ROS 2 stack, which currently supports both navigation and manipulation. At this stage, the agent is responsible for navigation only.
![Various objects](images/kairos.jpg)

The warehouse environment is designed to represent a realistic setting, with space for the robot to move, avoid obstacles, and perform tasks. The scene will be expanded to create a more real, non-automated setup, allowing the agent to operate in conditions that closely resemble actual warehouse scenarios.
![Various objects](images/scene.jpg)

Within the environment, there are multiple object models placed in different conditions, along with anomalies such as an oil spill. Boxes of various shapes and states are included to test perception, navigation, and adaptability.
A script for introducing anomalies into the scene will be fine-tuned later in the process to introduce realistic anomalies during robot operation.

![Various objects](images/objects.jpg)

For instructions on running the agent on a custom task, please see the [Setup instructions](setup.md) and [Running the demo section](running.md).
