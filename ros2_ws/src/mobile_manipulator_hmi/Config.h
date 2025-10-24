#pragma once


#include <QColor>
#include <map>
#include <unordered_set>
#include <vector>

namespace HardcodedConfig {


    // Camera display names and their corresponding ROS topics
    const static std::map<std::string, std::string> CameraTopics = {
        {"Camera 1", "/rgbd_camera/camera_image_color"},
        {"Camera 2", "/wrist_camera/camera_image_color"}
    };

    // Task display names and their system names
    const static std::map<std::string, QString> Tasks = {
        {"Task 1", "task1"},
        {"Task 2", "task2"},
        {"Task 3", "task3"},
    };


    const static std::map<std::string, QColor> Colors = {
        {"Safety", "#0072CE"},
        {"Inspection", "#FF6F00"},
        {"Box", "#B08855"},
        {"ActiveStep", "#007BFF"},
        {"PastSteps", "#A0A0A0"},
        {"ActiveTask", "#28C76F"},
        {"TaskQueue", "#FFC107"},
        {"Pause", "#9C27B0"},
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

    const static std::string taskAPrompt = "Do Sort Package Returns";
    const static std::string taskBPrompt = "Do Housekeeping of rack ";
    const static std::vector<std::string> racks = {"A01",
    "A02",
    "A03",
    "A04",
    "A05",
    "A06",
    "B01",
    "B02",
    "B03",
    "B04",
    "C01",
    "C02",
    "C03",
    "C04",
    "D01",
    "D02",
    "D03",
    "D04",
    "F01",
    "F02",
    "F03",
    "F04",
    "F05",
    "F06",
    "F07",
    "F08",
    "F09",
    "F10",
    "G01",
    "G02",
    "G03",
    "G04",
    "G05",
    "G06",
    "H01",
    "H02",
    "I01",
    "I02",
    "J01",
    "J02",
    "K01",
    "K02",
    "L01",
    "L02",
    "L03",
    "L04",
    "L05",
    "L06",
    "L07",
    "L08",
    "L09",
    "L10"};
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

    const static char HousekeepService[] = "/rai/scene/housekeep";
    const static char AnomaliesService[] = "/rai/scene/anomalies";
    const static char StandardService[] = "/rai/scene/standard";
    const static char CleanupService[] = "/rai/scene/cleanup";

    constexpr static int MaxVLMMessages = 100; // max amount of messages to be stored in memory
}
