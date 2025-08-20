# Resource monitoring script

This script examines resource consumption by RAI agent, VLM, LLM, moveit, nav2 setup

The setup consists of:

- Ollama server (running inference)
- Ollama llm and vlm client (VLM for image understanding, LLM for tool calling)
- nav2 process (ros2 nav2 package used for navigating robots)
- moveit process (ros2 moveit package used for handling manipulation robotic arms + manipulator package which makes it easier)

## Testing hardware setup

- testing hardware
- separate machine (desktop computer) to run simulation

## Installation

On **tested hardware** you will need:

- ros2 (jazzy or humble)
- ollama (https://ollama.com/)
- poetry (https://python-poetry.org/docs/#installing-with-pipx)

On **simulation machine** you will need:

- ros2 (jazzy or humble)

On **tested hardware**:

1. Install dependencies with poetry:

   ```bash
   git clone git@github.com:RobotecAI/MobileManipulatorDemo.git
   cd MobileManipulatorDemo/monitoring
   poetry install
   ```

2. Download and build manipulator client

   ```bash
   git clone https://github.com/RobotecAI/rai-manipulation-demo
   cd rai-manipulation-demo/
   rosdep install --from-paths ros2_ws/src --ignore-src -r -y
   cd ros2_ws/
   colcon build
   ```

On **both machines**:

> [!NOTE]
> Before installing make sure you have ROS_DISTRO env set.

1. Install ros dependencies.

   ```bash
   export ROS_DISTRO=jazzy # or humble
   source /opt/ros/${ROS_DISTRO}/setup.bash
   sudo apt update
   sudo apt install ros-${ROS_DISTRO}-moveit ros-${ROS_DISTRO}-moveit-resources-panda-moveit-config \
                           ros-${ROS_DISTRO}-ros2-control ros-${ROS_DISTRO}-ros2-controllers \
                           ros-${ROS_DISTRO}-controller-manager \
                           ros-${ROS_DISTRO}-moveit-commander \
                           ros-$ROS_DISTRO-navigation2 ros-$ROS_DISTRO-nav2-bringup
   ```

On **simulation machine** set up the simulation for nav2 and moveit testing

1. Download binaries:

   ```bash
   git clone https://github.com/RobotecAI/rai
   ./rai/scripts/download_demo.sh rosbot
   ./rai/scripts/download_demo.sh manipulation
   ```

## Running

1. Make sure both machines can communicate by ros2. (for example try running
   [talker and listener](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#try-some-examples)
   on 2 machines)

### On **simulation machine**

> [!NOTE]
> If you want to test working moveit or nav2, run respective binary like below,
> if not just skip this, the ros2 stack does not consume much more then idle, either way.

> [!WARNING]
> With current binaries only 1 running stack can be tested at once (either `nav2`
> or `moveit`). It's due to conflicting topics. Workarounds are possible but has
> been skipped, since common simulation is planned.
> Second package will be idle in both cases.

1. Start Simulation

   Start one of simulation:

   a. For navigation:

   ```bash
   source /opt/ros/${ROS_DISTRO}/setup.bash
   ./rai/demo_assets/rosbot/RAIROSBotXLDemo/RAIROSBotXLDemo.GameLauncher
   ```

   b. For manipulation:

   ```bash
   source /opt/ros/${ROS_DISTRO}/setup.bash
   ./rai/demo_assets/manipulation/RAIManipulationDemo/RAIManipulationDemo.GameLauncher
   ```

### On **tested hardware**

> [!WARNING]
> Before executing commands below make sure that ollama is not running: `sudo systemctl status ollama`
>
> Stop ollama server: `sudo systemctl stop ollama`

1. Download LLMs

   ```bash
   ollama serve

   # add other models, ones below are by default used in run.sh
   for model in \
       "qwen2.5vl:3b" "qwen2.5vl:7b" "qwen2.5:7b" "qwen2.5:14b" "qwen2.5:32b"; \
   do
       ollama pull "$model"
   done
   pkill -f ollama
   ```

2. Configure tested LLMs in `run.sh`

   You can run multiple set of models with `./run.sh` script, change the params of
   execution inside to suit your needs:

   ```bash
   # modify --model-* params in ./run.sh:
   python3 "$SCRIPT_NAME" --run-time 200 --model-vl "qwen2.5vl:3b" --model-llm "qwen2.5:7b"
   ```

3. Run the monitoring script with:

   ```bash
   source /opt/ros/${ROS_DISTRO}/setup.bash
   source rai-manipulation-demo/ros2_ws/install/setup.bash
   `poetry env activate`
   ./run.sh manipulation # or navigation (depending on chosen simulation)
   ```

4. After completion you can view results in `./monitoring_results-*` folder

> [!WARNING]
> When you rerun script, it will automatically kill previously spawned llama processes with `pkill -9 "ollama"`.
> ROS 2 nodes tend to not shutdown politely, in such case nav2 and moveit won't work properly.
>
> check with:
>
> ```bash
> ros2 node list
> ```
>
> In such case run:
>
> ```bash
> pkill -f "ros"`
> ros2 daemon stop`
> ros2 daemon start
> ```
