#pragma once

#include <string>
#include <map>
#include <unordered_set>

namespace HardcodedConfig {

    // Camera display names and their corresponding ROS topics
    const static std::map<std::string, std::string> CameraTopics = {
        {"Camera 1", "/rgbd_camera/camera_image_color"},
        {"Camera 2", "/wrist_camera/camera_image_color"}
    };

    // Task display names and their system names
    const static std::map<std::string, std::string> Tasks = {
        {"Task 1", "task1"},
        {"Task 2", "task2"},
        {"Task 3", "task3"},
    };


    const static std::map<std::string, std::string> Colors = {
        {"Safety", "#FFFF00"},
        {"Inspection", "#00FF00"},
        {"Box", "#00FFFF"},
    };

    const static char UserPromptTopic[] = "/user_tasks";
    const static char OrchestratorHeartbeat[] = "/orchestrator/heartbeat"; // TODO: Get actual topic names
                                                                           //
    const static char VLMTopic[] = "/vlm_topic";
    const static char EmergencyStopTopic[] = "/emergency_stop";

    // Frequencies are given in Hertz
    constexpr static float OrchestratorHeartbeatFrequency = 0.2f;
    constexpr static float InpsectionFrequency = 0.2f;
    constexpr static float SafetyFrequency = 0.2f;

    const static std::string taskAPrompt = "Do Sort Returns";
    const static std::string taskBPrompt = "Do Housekeeping";
    const static std::string taskCPrompt = "Prepare shipping of the following items: ";


    const static char MapTopic[] = "/global_costmap/static_layer";
    const static char GoalTopic[] = "/goal_pose";
    const static char PathTopic[] = "/plan";
    const static char CmdVelTopic[] = "/cmd_vel";

    const static char RobotBaseFrame[] = "egobase_link";

    const static std::unordered_set<std::string> LogFilter = {
        "rcl", "rcl_lifecycle", "rclcpp", "rmw_fastrtps_cpp", "nav2_costmap_2d", "nav2_util",
        "nav2_controller", "nav2_planner", "nav2_recoveries", "nav2_bt_navigator", "nav2_amcl", "hmi_window_node"
    };
    const static int MinLogLevel = 20; // only show WARN and above
    const static int MaxLogEntries = 10; // max log entries to keep in the list

    const static char Restart[] = "/restart";

    const static char AgentCurrentAction[] = "/agent/current_action"; //HRIMessage
    const static char AgentPastSteps[] = "/agent/past_steps"; // string('["step1", "step2"]')

    const static char OrchestratorCurrentTask[] = "/orchestrator/current_task"; // string
    const static char OrchestratorTaskQueue[] = "/orchestrator/tasks_queue"; // string('["step1", "step2"]')
    const static char OrchestratorPausedTask[] = "/orchestrator/paused_tasks"; // string('["step1", "step2"]')

    constexpr static int MaxVLMMessages = 100; // max amount of messages to be stored in memory
}
