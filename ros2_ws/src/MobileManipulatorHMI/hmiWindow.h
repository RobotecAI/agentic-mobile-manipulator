#ifndef HMIWINDOW_H
#define HMIWINDOW_H
#include <QGraphicsPixmapItem>
#include <QGraphicsScene>
#include <QGraphicsView>
#include <QMainWindow>
#include <QPushButton>
#include <QTimer>
#include <QWheelEvent>
#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <nav_msgs/msg/path.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>
#include <tf2_ros/transform_listener.h>
#include <tf2_ros/buffer.h>
#include <rcl_interfaces/msg/log.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include "TaskDialog.h"
QT_BEGIN_NAMESPACE
namespace Ui {
class HMIWindow;
}
QT_END_NAMESPACE


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
    const static char TaskTopic[] = "/predefined_task";
    const static char UserPromptTopic[] = "/user_prompt";


    const static char MapTopic[] = "/global_costmap/static_layer";
    const static char GoalTopic[] = "/goal_pose";
    const static char PathTopic[] = "/plan";
    const static char CmdVelTopic[] = "/cmd_vel";

    const static char RobotBaseFrame[] = "egobase_link";
    const static char ResourceTopics[] = "/resource_monitor";

    const static std::unordered_set<std::string> LogFilter = {
        "rcl", "rcl_lifecycle", "rclcpp", "rmw_fastrtps_cpp", "nav2_costmap_2d", "nav2_util",
        "nav2_controller", "nav2_planner", "nav2_recoveries", "nav2_bt_navigator", "nav2_amcl", "hmi_window_node"
    };
    const static int MinLogLevel = 20; // only show WARN and above
    const static int MaxLogEntries = 10; // max log entries to keep in the list

    const static char EmergencyStopService[] = "/emergency_stop";
    const static char Restart[] = "/restart";

    const static char AgentCurrentStep[] = "/agent/current_step";
    const static char AgentTotalSteps[] = "/agent/past_steps";
}

class HMIWindow : public QMainWindow
{
    Q_OBJECT

public:
    HMIWindow(QWidget *parent = nullptr);
    ~HMIWindow();

private slots:
    void spinROS();
    void openCustomTaskDialog();

private:
    void cameraButtonCallback(const std::string& cameraName);
    void imageCallback(const sensor_msgs::msg::Image::SharedPtr msg, QGraphicsView* view);
    void mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);
    void logCallback(const rcl_interfaces::msg::Log::SharedPtr msg);
    void publishCmdVel(double linear_x, double angular_z);
    void setCurrentTaskName(const QString& name);
    void setDoneTasks(const QStringList& done);

    void updateRobotPose();
    
    Ui::HMIWindow *ui;
    rclcpp::Node::SharedPtr node_;
    QTimer *ros_timer_;
    std::map<std::string, QPushButton*> camera_buttons_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr goal_pub_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr task_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr user_prompt_pub_;

    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr currenttask_sub_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr donetasks_sub_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr emergency_stop_srv_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr restart_srv_;

    rclcpp::Subscription<rcl_interfaces::msg::Log>::SharedPtr log_sub_;
    rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr resource_sub_;

    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};
#endif // HMIWINDOW_H
