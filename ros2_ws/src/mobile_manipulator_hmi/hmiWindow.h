// Copyright (C) 2025 Advanced Micro Devices, Inc.
// Developed by Robotec.ai sp. z o.o.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//         http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
#include <demo_msgs/msg/utilization.hpp>
#include <demo_msgs/msg/vlm_description.hpp>
#include <rai_interfaces/msg/hri_message.hpp>
#include "TaskDialog.h"
#include "LogItemWidget.h"
#include "Config.h"
#include "LogQueue.h"
#include "LogView.h"
#include "UiKit.h"
#include "ZoomableGraphicsView.h"

class QCheckBox;
class QLineEdit;
class QListWidget;
class QVBoxLayout;
class QLabel;

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
    // --- UI construction ---
    QWidget* buildHeader();
    QWidget* buildControlTab();
    QWidget* buildStatusTab();
    QWidget* buildMissionTab();

    // --- ROS handling ---
    void initRos();
    void cameraButtonCallback(const std::string& cameraName);
    void imageCallback(const sensor_msgs::msg::Image::SharedPtr msg, QGraphicsView* view);
    void mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);
    void logCallback(const rcl_interfaces::msg::Log::SharedPtr msg);
    void publishCmdVel(double linear_x, double angular_z);
    void publishPrompt(const std::string& prompt);

    void updateRobotPose();
    void buildListTask();

    int current_rack_index_ {0};

    QString currentActionText_;
    QString currentActionCommId_;

    rclcpp::Node::SharedPtr node_;
    QTimer *ros_timer_ {nullptr};
    QTimer *orchestrator_timer_ {nullptr};

    // --- widgets referenced by callbacks ---
    // mission observer
    QGraphicsView* graphicsViewCameras_ {nullptr};
    QGraphicsView* topCameraGraphicsView_ {nullptr};
    ZoomableGraphicsView* graphicsViewMap_ {nullptr};

    // control tab inputs
    QCheckBox* cpuCheck_ {nullptr};
    QCheckBox* gpuCheck_ {nullptr};
    QCheckBox* pipesCheck_ {nullptr};
    QCheckBox* hammersCheck_ {nullptr};
    QCheckBox* nailsCheck_ {nullptr};
    QCheckBox* motherboardCheck_ {nullptr};
    QLineEdit* freeFormEdit_ {nullptr};
    QPushButton* restartButton_ {nullptr};
    QLabel* housekeepingHint_ {nullptr};

    // status tab telemetry
    ui::StatBar* cpuBar_ {nullptr};
    ui::StatBar* ramBar_ {nullptr};
    ui::StatBar* gpuBar_ {nullptr};
    ui::StatBar* diskBar_ {nullptr};
    ui::StatBar* vramBar_ {nullptr};
    ui::StatusPill* nav2Pill_ {nullptr};
    ui::StatusPill* moveit2Pill_ {nullptr};
    ui::StatusPill* orchestratorPill_ {nullptr};
    ui::StatusPill* ddsPill_ {nullptr};
    ui::StatusPill* watchdogPill_ {nullptr};
    ui::StatusPill* entitiesPill_ {nullptr};
    ui::StatusPill* agentPill_ {nullptr}; // lives in the header
    QListWidget* listLog_ {nullptr};
    QLabel* lastWarningLabel_ {nullptr};

    // mission tab
    ui::StatTile* taskTile_ {nullptr};
    LogView* logView_ {nullptr};
    LogView* queueView_ {nullptr};
    LogItemWidget* currentAction_ {nullptr};
    LogItemWidget* currentTask_ {nullptr};
    QVBoxLayout* listTaskLayout_ {nullptr};
    QVBoxLayout* vlmLayout_ {nullptr};

    QStringList past_steps_;
    QStringList task_queue_;
    QStringList paused_tasks_;

    std::map<std::string, QPushButton*> camera_buttons_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr top_image_sub_;
    rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr goal_pub_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr user_prompt_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr stop_pub_;

    rclcpp::Subscription<std_msgs::msg::Header>::SharedPtr orchestrator_sub_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr restart_srv_;

    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr housekeep_srv_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr anomalies_srv_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr standard_srv_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr cleanup_srv_;

    rclcpp::Subscription<rcl_interfaces::msg::Log>::SharedPtr log_sub_;
    rclcpp::Subscription<demo_msgs::msg::Utilization>::SharedPtr utilization_sub_;

    rclcpp::Subscription<demo_msgs::msg::VlmDescription>::SharedPtr vlm_topic_sub_;

    rclcpp::Subscription<rai_interfaces::msg::HRIMessage>::SharedPtr current_action_sub_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr agent_past_steps_sub_;

    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr orchestrator_current_task_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr orchestrator_task_queue_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr orchestrator_paused_task_;

    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};
#endif // HMIWINDOW_H
