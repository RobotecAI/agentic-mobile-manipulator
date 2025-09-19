# Demo Content

The demo showcases a Robotnik Kairos+ mobile manipulator operating within a small warehouse facility. The system runs on a ROS 2 stack, supporting navigation, manipulation, and combined tasks. The agent is now capable of handling these tasks effectively.
![Various objects](images/kairos.jpg)

The warehouse environment is designed to represent a realistic setting, providing space for the robot to move, avoid obstacles, and perform tasks. The scene has been expanded to create a more realistic, non-automated setup, allowing the agent to operate in conditions that closely resemble actual warehouse scenarios.
![Various objects](images/scene.jpg)

Within the environment, multiple object models are placed in various conditions, along with anomalies such as an oil spill. Boxes of different shapes and states are included to test perception, navigation, and adaptability.
A script for introducing anomalies into the scene will be fine-tuned later in the process to introduce realistic anomalies during robot operation.

![Various objects](images/objects.jpg)

For instructions on running the agent on a custom task, please refer to the [Setup instructions](setup.md) and [Running the demo section](running.md).
