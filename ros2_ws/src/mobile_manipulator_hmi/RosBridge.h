// Copyright (C) 2026 Advanced Micro Devices, Inc.
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

#pragma once

#include <QHash>
#include <QNetworkAccessManager>
#include <QObject>
#include <QPointF>
#include <QStringList>
#include <QTimer>
#include <QVariantList>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <nav_msgs/msg/path.hpp>
#include <rcl_interfaces/msg/log.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/empty.hpp>
#include <std_msgs/msg/header.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include <demo_msgs/msg/utilization.hpp>
#include <demo_msgs/msg/vlm_description.hpp>
#include <rai_interfaces/msg/hri_message.hpp>

#include "AgentEventModel.h"
#include "RosImageProvider.h"

// Everything the QML UI shows or does goes through this object: it owns the ROS 2 node,
// spins it from the Qt event loop, and exposes state as properties and commands as
// invokables. Topic and message contract: docs/setup_hmi.md.
class RosBridge : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString simTime READ simTime NOTIFY simTimeChanged)
    Q_PROPERTY(bool estopped READ estopped NOTIFY estopChanged)
    Q_PROPERTY(QString currentTask READ currentTask NOTIFY tasksChanged)
    Q_PROPERTY(QStringList queue READ queue NOTIFY tasksChanged)
    Q_PROPERTY(QStringList pastSteps READ pastSteps NOTIFY tasksChanged)
    Q_PROPERTY(qint64 taskStartMs READ taskStartMs NOTIFY tasksChanged)
    Q_PROPERTY(qint64 nowMs READ nowMs NOTIFY tick)
    Q_PROPERTY(QVariantList resources READ resources NOTIFY resourcesChanged)
    Q_PROPERTY(QVariantList agents READ agents NOTIFY tick)
    Q_PROPERTY(QVariantList endpoints READ endpoints NOTIFY endpointsChanged)
    Q_PROPERTY(QVariantList logs READ logs NOTIFY logsChanged)
    Q_PROPERTY(int cameraIndex READ cameraIndex WRITE setCameraIndex NOTIFY cameraChanged)
    Q_PROPERTY(QString cameraTopic READ cameraTopic NOTIFY cameraChanged)
    Q_PROPERTY(int cameraFrame READ cameraFrame NOTIFY cameraFrameChanged)
    Q_PROPERTY(int mapFrame READ mapFrame NOTIFY mapChanged)
    Q_PROPERTY(QSize mapSize READ mapSize NOTIFY mapChanged)
    Q_PROPERTY(QPointF robotPixel READ robotPixel NOTIFY poseChanged)
    Q_PROPERTY(double robotYaw READ robotYaw NOTIFY poseChanged)
    Q_PROPERTY(QString robotPose READ robotPose NOTIFY poseChanged)
    Q_PROPERTY(QVariantList pathPixels READ pathPixels NOTIFY pathChanged)
    Q_PROPERTY(QString loadedScene READ loadedScene NOTIFY sceneChanged)
    Q_PROPERTY(QString sceneBusy READ sceneBusy NOTIFY sceneChanged)
    Q_PROPERTY(QString llmModel READ llmModel CONSTANT)
    Q_PROPERTY(bool rosOk READ rosOk NOTIFY tick)
    Q_PROPERTY(QObject *events READ events CONSTANT)
    Q_PROPERTY(QObject *streamFilter READ streamFilter CONSTANT)
    Q_PROPERTY(QObject *traceFilter READ traceFilter CONSTANT)

public:
    RosBridge(RosImageProvider *images, QObject *parent = nullptr);
    ~RosBridge() override;

    QString simTime() const { return simTime_; }
    bool estopped() const { return estopped_; }
    QString currentTask() const { return currentTask_; }
    QStringList queue() const { return queue_; }
    QStringList pastSteps() const { return pastSteps_; }
    qint64 taskStartMs() const { return taskStartMs_; }
    qint64 nowMs() const { return events_->nowMs(); }
    QVariantList resources() const;
    QVariantList agents() const;
    QVariantList endpoints() const { return endpoints_; }
    QVariantList logs() const { return logs_; }
    int cameraIndex() const { return cameraIndex_; }
    void setCameraIndex(int index);
    QString cameraTopic() const;
    int cameraFrame() const { return cameraFrame_; }
    int mapFrame() const { return mapFrame_; }
    QSize mapSize() const { return mapSize_; }
    QPointF robotPixel() const { return robotPixel_; }
    double robotYaw() const { return robotYaw_; }
    QString robotPose() const { return robotPose_; }
    QVariantList pathPixels() const { return pathPixels_; }
    QString loadedScene() const { return loadedScene_; }
    QString sceneBusy() const { return sceneBusy_; }
    QString llmModel() const { return llmModel_; }
    bool rosOk() const { return rclcpp::ok(); }
    QObject *events() const { return events_; }
    QObject *streamFilter() const { return streamFilter_; }
    QObject *traceFilter() const { return traceFilter_; }

    Q_INVOKABLE void sendTask(const QString &prompt);
    Q_INVOKABLE void loadScene(const QString &name);
    Q_INVOKABLE void emergencyStop();
    Q_INVOKABLE void releaseStop();
    Q_INVOKABLE void drive(double linear, double angular);
    Q_INVOKABLE void sendGoal(double mapPx, double mapPy);
    Q_INVOKABLE QString agentColor(const QString &agent) const;

signals:
    void simTimeChanged();
    void estopChanged();
    void tasksChanged();
    void tick();
    void resourcesChanged();
    void endpointsChanged();
    void logsChanged();
    void cameraChanged();
    void cameraFrameChanged();
    void mapChanged();
    void poseChanged();
    void pathChanged();
    void sceneChanged();
    // One-line feedback for the operator (scene loaded, service missing, ...).
    void notify(const QString &message, bool error);

private:
    void spin();
    void onEvent(const std::string &json);
    void onAction(const rai_interfaces::msg::HRIMessage &msg);
    void onVlm(const demo_msgs::msg::VlmDescription &msg);
    void onLog(const rcl_interfaces::msg::Log &msg);
    void onImage(const sensor_msgs::msg::Image &msg, const QString &id, bool rotate);
    void onMap(const nav_msgs::msg::OccupancyGrid &msg);
    void onPath(const nav_msgs::msg::Path &msg);
    void setCurrentTask(const QString &task);
    void markActive(const QString &agent, const QString &doing);
    void updatePose();
    void pollEndpoints();
    void subscribeCamera();
    QPointF worldToPixel(double x, double y) const;
    static QString agentForNode(const QString &node);

    RosImageProvider *images_;
    AgentEventModel *events_;
    AgentFilterModel *streamFilter_;
    AgentFilterModel *traceFilter_;

    rclcpp::Node::SharedPtr node_;
    QTimer spinTimer_;
    QTimer secondTimer_;
    QTimer endpointTimer_;
    QNetworkAccessManager network_;

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr taskPub_;
    rclcpp::Publisher<std_msgs::msg::Empty>::SharedPtr estopPub_;
    rclcpp::Publisher<std_msgs::msg::Empty>::SharedPtr releasePub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmdVelPub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr goalPub_;
    QHash<QString, rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr> sceneClients_;
    std::vector<rclcpp::SubscriptionBase::SharedPtr> subs_;
    rclcpp::SubscriptionBase::SharedPtr cameraSub_;
    std::unique_ptr<tf2_ros::Buffer> tfBuffer_;
    std::shared_ptr<tf2_ros::TransformListener> tfListener_;

    QString simTime_ = "--:--:--";
    bool estopped_ = false;
    QString currentTask_;
    QStringList queue_;
    QStringList pastSteps_;
    qint64 taskStartMs_ = 0;
    bool eventsSeen_ = false;  // once /agent/events speaks, /agent/current_action is ignored

    struct Resource { QString name; double value = -1; QVariantList history; };
    QVector<Resource> resources_;
    bool nav2Ok_ = false;
    bool moveit2Ok_ = false;
    qint64 utilizationMs_ = -1;

    struct AgentState { qint64 heartbeatMs = -1; qint64 activeMs = -1; QString doing; };
    QHash<QString, AgentState> agentStates_;
    QVariantList endpoints_;
    QVariantList logs_;
    bool logsDirty_ = false;

    int cameraIndex_ = 0;
    int cameraFrame_ = 0;
    qint64 lastFrameMs_ = 0;
    int mapFrame_ = 0;
    QSize mapSize_;
    double mapResolution_ = 0;
    double mapOriginX_ = 0;
    double mapOriginY_ = 0;
    QPointF robotPixel_{-1, -1};
    double robotYaw_ = 0;
    QString robotPose_ = "pose unknown";
    QVariantList pathPixels_;
    QString loadedScene_ = "none";
    QString sceneBusy_;
    QString llmModel_;
    int vlmCounter_ = 0;
};
