// Copyright (C) 2025 Robotec.ai sp. z o.o. — Apache-2.0
//
// Bridges the ROS 2 graph to QML: exposes live telemetry / mission state as
// Q_PROPERTYs + signals, and outbound commands as Q_INVOKABLE methods. ROS is
// spun on the Qt GUI thread (QTimer), so all callbacks run on the GUI thread
// and no extra locking is required.
#pragma once

#include <QImage>
#include <QMutex>
#include <QObject>
#include <QStringList>
#include <QVariantList>
#include <chrono>
#include <memory>

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <nav_msgs/msg/path.hpp>
#include <rcl_interfaces/msg/log.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/header.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include <demo_msgs/msg/utilization.hpp>
#include <demo_msgs/msg/vlm_description.hpp>
#include <rai_interfaces/msg/hri_message.hpp>

class RosBridge : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool hasTelemetry READ hasTelemetry NOTIFY telemetryChanged)
    Q_PROPERTY(double cpu READ cpu NOTIFY telemetryChanged)
    Q_PROPERTY(double ram READ ram NOTIFY telemetryChanged)
    Q_PROPERTY(double gpu READ gpu NOTIFY telemetryChanged)
    Q_PROPERTY(double vram READ vram NOTIFY telemetryChanged)
    Q_PROPERTY(double disk READ disk NOTIFY telemetryChanged)
    Q_PROPERTY(bool nav2Ok READ nav2Ok NOTIFY telemetryChanged)
    Q_PROPERTY(bool moveit2Ok READ moveit2Ok NOTIFY telemetryChanged)
    Q_PROPERTY(bool agentOnline READ agentOnline NOTIFY agentOnlineChanged)
    Q_PROPERTY(QString currentTask READ currentTask NOTIFY currentTaskChanged)
    Q_PROPERTY(QString currentAction READ currentAction NOTIFY currentActionChanged)
    Q_PROPERTY(QStringList pastSteps READ pastSteps NOTIFY planChanged)
    Q_PROPERTY(QStringList taskQueue READ taskQueue NOTIFY planChanged)
    Q_PROPERTY(QVariantList vlmFeed READ vlmFeed NOTIFY vlmChanged)
    Q_PROPERTY(QVariantList events READ events NOTIFY eventsChanged)
    Q_PROPERTY(int cameraRev READ cameraRev NOTIFY cameraChanged)
    Q_PROPERTY(int mapRev READ mapRev NOTIFY mapChanged)

public:
    explicit RosBridge(QObject* parent = nullptr);
    ~RosBridge() override;

    bool hasTelemetry() const { return has_telemetry_; }
    double cpu() const { return cpu_; }
    double ram() const { return ram_; }
    double gpu() const { return gpu_; }
    double vram() const { return vram_; }
    double disk() const { return disk_; }
    bool nav2Ok() const { return nav2_ok_; }
    bool moveit2Ok() const { return moveit2_ok_; }
    bool agentOnline() const { return agent_online_; }
    QString currentTask() const { return current_task_; }
    QString currentAction() const { return current_action_; }
    QStringList pastSteps() const { return past_steps_; }
    QStringList taskQueue() const { return task_queue_; }
    QVariantList vlmFeed() const { return vlm_feed_; }
    QVariantList events() const { return events_; }
    int cameraRev() const { return camera_rev_; }
    int mapRev() const { return map_rev_; }

    // image access for the QQuickImageProvider
    QImage cameraImage(const QString& name) const;
    QImage mapImage() const;

public slots:
    void sendPrompt(const QString& text);
    void runScenario(const QString& key); // standard|housekeep|anomalies|cleanup
    void restart();
    void estop();
    void teleop(double linear, double angular);

signals:
    void telemetryChanged();
    void agentOnlineChanged();
    void currentTaskChanged();
    void currentActionChanged();
    void planChanged();
    void vlmChanged();
    void eventsChanged();
    void cameraChanged();
    void mapChanged();

private:
    void spin();
    void checkHeartbeat();
    void callTrigger(rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr client, const QString& label);
    static QStringList parseList(const QString& raw);
    static QImage toQImage(const sensor_msgs::msg::Image& msg);

    rclcpp::Node::SharedPtr node_;
    QTimer* spin_timer_ {nullptr};
    QTimer* hb_timer_ {nullptr};

    // state
    bool has_telemetry_ {false};
    double cpu_ {-1}, ram_ {-1}, gpu_ {-1}, vram_ {-1}, disk_ {-1};
    bool nav2_ok_ {false}, moveit2_ok_ {false};
    bool agent_online_ {false};
    std::chrono::steady_clock::time_point last_hb_ {};
    QString current_task_, current_action_, current_action_id_;
    QStringList past_steps_, task_queue_;
    QVariantList vlm_feed_, events_;

    // image state is read from the QQuickImageProvider thread and written from
    // the GUI thread (ROS callbacks) -> guard with a mutex
    mutable QMutex img_mutex_;
    QHash<QString, QImage> camera_images_;
    int camera_rev_ {0};

    nav_msgs::msg::OccupancyGrid::SharedPtr map_;
    nav_msgs::msg::Path::SharedPtr plan_;
    int map_rev_ {0};

    // ROS i/o
    rclcpp::Subscription<demo_msgs::msg::Utilization>::SharedPtr util_sub_;
    rclcpp::Subscription<std_msgs::msg::Header>::SharedPtr hb_sub_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr task_sub_, past_sub_, queue_sub_;
    rclcpp::Subscription<rai_interfaces::msg::HRIMessage>::SharedPtr action_sub_;
    rclcpp::Subscription<demo_msgs::msg::VlmDescription>::SharedPtr vlm_sub_;
    rclcpp::Subscription<rcl_interfaces::msg::Log>::SharedPtr log_sub_;
    rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr plan_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr base_cam_sub_, wrist_cam_sub_, top_cam_sub_;

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr prompt_pub_, stop_pub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr restart_cli_, standard_cli_, housekeep_cli_, anomalies_cli_, cleanup_cli_;

    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};
