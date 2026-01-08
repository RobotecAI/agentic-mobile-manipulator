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

#include "hmiWindow.h"
#include "./ui_hmiWindow.h"
#include <tf2/exceptions.h>
#include <chrono>
#include <thread>
#include <cmath>
#include <optional>
#include <unordered_map>
#include <QMessageBox>
#include <rclcpp/qos.hpp>
#include <QTransform>
#include <QTime>
#include "LogView.h"
#include "ParseRaiData.h"

QString HRIMessageToString(const ParseRaiData::HRIMessage& msg)
{
    QStringList paramList;
    for (auto it = msg.parameters_.cbegin(); it != msg.parameters_.cend(); ++it) {
        paramList << QString("%1: %2").arg(it.key(), it.value());
    }

    QString paramsStr = paramList.isEmpty()
        ? "none"
        : paramList.join(", ");

    return QString("Calling Tool %1 with params %2")
        .arg(msg.tool_name_, paramsStr);
}

void CallService(QWidget *parent, rclcpp::Node::SharedPtr &node,
                 rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr &client)
{
    const bool ok = client->wait_for_service(std::chrono::seconds(1));
    if (!ok) {
        QMessageBox::warning(parent, "Service Call Failed", "Service not available.");
        return;
    }

    auto request = std::make_shared<std_srvs::srv::Trigger::Request>();
    auto result_future = client->async_send_request(request);

    // Wait for up to 10 seconds for the result
    auto status = rclcpp::spin_until_future_complete(
        node, result_future, std::chrono::seconds(20));

    if (status != rclcpp::FutureReturnCode::SUCCESS) {
        QMessageBox::warning(parent, "Service Call Timeout",
                             "Service did not respond within 10 seconds.");
        return;
    }

    // If successful, you can access the response
    auto response = result_future.get();
    if (!response->success) {
        QMessageBox::warning(parent, "Service Call Failed", QString::fromStdString(response->message));
    }
}

const std::unordered_map<std::string, int> EncodingMap = {
    {"mono8", QImage::Format_Grayscale8},
    {"rgb8", QImage::Format_RGB888},
    {"rgba8", QImage::Format_RGBA8888},
    {"bgra8", QImage::Format_RGBA8888}, // Will need to swap channels
    // Add more mappings as needed
};

QStringList parsePythonList(QString list){
  QStringList done;
  QString listStr = list.trimmed();
  
  // Remove brackets [ ]
  if (listStr.startsWith('[') && listStr.endsWith(']')) {
      listStr = listStr.mid(1, listStr.length() - 2);
  }
  
  // Split by comma and clean up each item
  if (!listStr.isEmpty()) {
      QStringList rawItems = listStr.split('|');
      for (const QString& item : rawItems) {
          QString cleanItem = item.trimmed();
          // Remove quotes if present
          if (cleanItem.startsWith('"') && cleanItem.endsWith('"')) {
              cleanItem = cleanItem.mid(1, cleanItem.length() - 2);
          } else if (cleanItem.startsWith('\'') && cleanItem.endsWith('\'')) {
              cleanItem = cleanItem.mid(1, cleanItem.length() - 2);
          }
          if (!cleanItem.isEmpty()) {
              done.append(cleanItem);
          }
      }
  }
  return done;
}

HMIWindow::HMIWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::HMIWindow)
{
    ui->setupUi(this);
    ui->pushButtonTeleopHide->hide();
    // init ros node
    rclcpp::init(0, nullptr);
    node_ = rclcpp::Node::make_shared("hmi_window_node");

    // connect pre-defined camera buttons from UI
    camera_buttons_["Camera 1"] = ui->wristCameraButton;
    connect(ui->wristCameraButton, &QPushButton::clicked, [this]() {
        cameraButtonCallback("Camera 1");
    });
    camera_buttons_["Camera 2"] = ui->baseCameraButton;
    connect(ui->baseCameraButton, &QPushButton::clicked, [this]() {
        cameraButtonCallback("Camera 2");
    });

    // Setup cmd_vel publisher
    cmd_vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>(HardcodedConfig::CmdVelTopic, 10);

    // Setup map subscriber - Map
    map_sub_ = node_->create_subscription<nav_msgs::msg::OccupancyGrid>(
        HardcodedConfig::MapTopic, 10,
        [this](const nav_msgs::msg::OccupancyGrid::SharedPtr msg) {
            mapCallback(msg);
        });

    path_sub_ = node_->create_subscription<nav_msgs::msg::Path>(HardcodedConfig::PathTopic, 10,
        [this](const nav_msgs::msg::Path::SharedPtr msg) {
            ui->graphicsViewMap->drawPlan(msg);
        });
    goal_pub_ = node_->create_publisher<geometry_msgs::msg::PoseStamped>(HardcodedConfig::GoalTopic, 10);

    stop_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::EmergencyStopTopic, 10);

    user_prompt_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::UserPromptTopic, 10);

    // Top camera subscription created below with explicit QoS

    // Utilization table has 3 rows in UI: CPU, RAM, GPU (in that order)
    // Subscribe to new demo_msgs/msg/Utilization message on /utilization
    utilization_sub_ = node_->create_subscription<demo_msgs::msg::Utilization>(
        "/utilization", 10,
        [this](const demo_msgs::msg::Utilization::SharedPtr msg) {
            // Build name -> value map
            std::unordered_map<std::string, float> values;
            const size_t n = std::min(msg->component_names.size(), msg->component_values.size());
            values.reserve(n);
            for (size_t i = 0; i < n; ++i) {
                values[msg->component_names[i]] = msg->component_values[i];
            }

            auto get = [&values](const char* key) -> std::optional<float> {
                auto it = values.find(key);
                if (it == values.end()) return std::nullopt;
                return it->second;
            };

            // Update table rows (0: CPU, 1: RAM, 2: GPU)
            if (auto v = get("cpu"); v.has_value()) {
                setFrameUtilization(ui->cpuFrame, *v);
            }
            if (auto v = get("ram"); v.has_value()) {
                setFrameUtilization(ui->ramFrame, *v);
            }
            if (auto v = get("gpu"); v.has_value()) {
                setFrameUtilization(ui->gpuFrame, *v);
            }
            if (auto v = get("npu"); v.has_value()) {
                if (v.value() == -1.0) {
                    // Grey out when NPU not present/not reported
                    setFrameDisabled(ui->npuFrame);
                } else {
                    setFrameUtilization(ui->npuFrame, *v);
                }
            }

            // Binary states for Nav2 and MoveIt2
            setFrameBinaryState(ui->nav2Frame, msg->nav2_state);
            setFrameBinaryState(ui->moveit2Frame, msg->moveit2_state);
        });
    // Setup log subscriber
    log_sub_ = node_->create_subscription<rcl_interfaces::msg::Log>(
        "/rosout", 10,
        [this](const rcl_interfaces::msg::Log::SharedPtr msg) {
            logCallback(msg);
        });
    // Setup tf2 listener
    tf_buffer_ = std::make_unique<tf2_ros::Buffer>(node_->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    // Connect teleop buttons with lambdas
    connect(ui->pushButtonTeleopFw, &QPushButton::pressed, [this]() { publishCmdVel(0.5, 0.0); });
    connect(ui->pushButtonTeleopBk, &QPushButton::pressed, [this]() { publishCmdVel(-0.5, 0.0); });
    connect(ui->pushButtonTeleopLeft, &QPushButton::pressed, [this]() { publishCmdVel(0.0, 0.5); });
    connect(ui->pushButtonTeleopRight, &QPushButton::pressed, [this]() { publishCmdVel(0.0, -0.5); });

    connect(ui->graphicsViewMap, &ZoomableGraphicsView::goalSet, [this](float x, float y) {
        RCLCPP_INFO(node_->get_logger(), "Goal set at (%.2f, %.2f)", x, y);
        auto goal_msg = geometry_msgs::msg::PoseStamped();
        goal_msg.header.frame_id = "map";
        goal_msg.pose.position.x = x;
        goal_msg.pose.position.y = y;
        goal_msg.pose.position.z = 0.0;
        goal_msg.pose.orientation.w = 1.0; // facing forward
        goal_pub_->publish(goal_msg);
    });

    connect(ui->taskAButton, &QPushButton::pressed, [this](){
        std_msgs::msg::String msg;
        msg.data = HardcodedConfig::taskAPrompt;
        user_prompt_pub_->publish(msg);
        });

    connect(ui->taskBButton, &QPushButton::pressed, [this](){
          std_msgs::msg::String msg;
          msg.data = HardcodedConfig::taskBPrompt + HardcodedConfig::racks[current_rack_index_];
          user_prompt_pub_->publish(msg);
          current_rack_index_ += 1;
          current_rack_index_ %= HardcodedConfig::racks.size();
        });

    connect(ui->taskCButton, &QPushButton::pressed, [this](){
        std_msgs::msg::String msg;
        std::string data = HardcodedConfig::taskCPrompt;
        if (ui->cpu_checkbox->isChecked()){
          data = data + "one CPU, ";
        }
        if (ui->gpu_checkbox->isChecked()){
          data = data + "one GPU, ";
        }
        if (ui->pipes_checkbox->isChecked()){
          data = data + "pipes, ";
        }
        if (ui->hammers_checkbox->isChecked()){
          data = data + "hammers, ";
        }
        if (ui->nails_checkbox->isChecked()){
          data = data + "nails, ";
        }
        if (ui->motherboard_checkbox->isChecked()){
          data = data + "motherboard, ";
        }
        msg.data = data;
        user_prompt_pub_->publish(msg);
        });

    connect(ui->StopButton, &QPushButton::pressed, [this](){ stop_pub_->publish(std_msgs::msg::String()); });

    // connect teleop buttons
    for (auto button : {ui->pushButtonTeleopFw, ui->pushButtonTeleopBk, ui->pushButtonTeleopLeft, ui->pushButtonTeleopRight}) {
        connect(button, &QPushButton::released, [this]() { publishCmdVel(0.0, 0.0); });
    }


    // connect custom task button from UI
    // connect(ui->taskCustomButton, &QPushButton::clicked, this, &HMIWindow::openCustomTaskDialog);

    // Enable zooming on graphics views
    ui->graphicsViewMap->setDragMode(QGraphicsView::RubberBandDrag);
    ui->graphicsViewMap->setRenderHint(QPainter::Antialiasing);
    ui->graphicsViewMap->setTransformationAnchor(QGraphicsView::AnchorUnderMouse);

    logView_  = new LogView(this);
    queueView_  = new LogView(this);
    currentAction_ = new LogItemWidget(QString(), QPixmap(), QColor("green"), TextMode::Detail, false ,this);
    currentAction_->setFixedHeight(100);
    currentAction_->setText("No current action.");

    currentTask_ = new LogItemWidget(QString(), QPixmap(), QColor("yellow"), TextMode::Wrap, false ,this);
    currentTask_->setFixedHeight(100);
    currentTask_->setText("No current task.");

    //connect(logQueue_, &LogQueue::logEnqueued, logView, &LogView::onLogEnqueued);

    ui->vlm_layout->addWidget(logView_);
    ui->listTask->addWidget(currentAction_);
    ui->listTask->addWidget(currentTask_);
    ui->listTask->addWidget(queueView_);


    vlm_topic_sub_ = node_->create_subscription<demo_msgs::msg::VlmDescription>(
        HardcodedConfig::VLMTopic, 10,
        [this](const demo_msgs::msg::VlmDescription::SharedPtr msg){
          RCLCPP_INFO(node_->get_logger(), "Data from (%s)", msg->source.c_str());
          QString label = QString(msg->description.c_str());
          QImage image = QImage();
          if (auto encoding = EncodingMap.find(msg->image.encoding); encoding != EncodingMap.end()) {
              image = QImage(msg->image.data.data(), static_cast<int>(msg->image.width), static_cast<int>(msg->image.height), static_cast<QImage::Format>(EncodingMap.at(msg->image.encoding)));

          }
          LogItemWidget* l1 = new LogItemWidget(label, QPixmap::fromImage(image), HardcodedConfig::Colors.at(msg->source), TextMode::Detail, true, this);
          logView_->addItem(l1);
        });


    // clients for services
    restart_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::Restart);
    housekeep_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::HousekeepService);
    anomalies_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::AnomaliesService);
    standard_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::StandardService);
    cleanup_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::CleanupService);

    // buttons
    connect(ui->RestartButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, restart_srv_);
    });

    connect(ui->housekeepButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, housekeep_srv_);
    });

    connect(ui->anomaliesButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, anomalies_srv_);
    });

    connect(ui->standardButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, standard_srv_);
    });

    connect(ui->cleanupButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, cleanup_srv_);
    });
    // done tasks and current task subscribers
    // currenttask_sub_ = node_->create_subscription<std_msgs::msg::String>(
    //     HardcodedConfig::AgentCurrentStep, 10,
    //     [this](const std_msgs::msg::String::SharedPtr msg) {
    //         setCurrentTaskName(msg->data.c_str());
    //     });
    //
    current_action_sub_ = node_->create_subscription<rai_interfaces::msg::HRIMessage>(
          HardcodedConfig::AgentCurrentAction, 10,
          [this](const rai_interfaces::msg::HRIMessage::SharedPtr msg) {
            QString new_id = QString(msg->communication_id.c_str());
            if( currentActionCommId_ != new_id ){
              
              currentActionText_ = QString(msg->text.c_str());
              std::optional<ParseRaiData::HRIMessage> parsed = ParseRaiData::parseHRIMessage(currentActionText_);
              if(parsed.has_value()){
                currentActionText_ = HRIMessageToString(parsed.value());
              }
              currentActionCommId_ = new_id;
            }else{
              currentActionText_ += QString(msg->text.c_str());
            }
            
            currentAction_->setText(currentActionText_);
          }
        );

    orchestrator_current_task_ = node_->create_subscription<std_msgs::msg::String>(
          HardcodedConfig::OrchestratorCurrentTask, 10,
          [this](const  std_msgs::msg::String::SharedPtr msg) {
            currentTask_->setText(msg->data.c_str());
          }
        );


    agent_past_steps_sub_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::AgentPastSteps, 10,
         [this](const std_msgs::msg::String::SharedPtr msg) {
             QString listStr = QString::fromStdString(msg->data);
             past_steps_ = parsePythonList(listStr);
             buildListTask();
         }
        );


    orchestrator_task_queue_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::OrchestratorTaskQueue, 10,
         [this](const std_msgs::msg::String::SharedPtr msg) {
             QString listStr = QString::fromStdString(msg->data);
             task_queue_ = parsePythonList(listStr);
             buildListTask();
         }
        );

     orchestrator_paused_task_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::OrchestratorPausedTask, 10,
         [this](const std_msgs::msg::String::SharedPtr msg) {
             QString listStr = QString::fromStdString(msg->data);
             paused_tasks_ = parsePythonList(listStr);
             buildListTask();
         }
        );

    // Setup ROS spinning timer
    ros_timer_ = new QTimer(this);
    connect(ros_timer_, &QTimer::timeout, this, &HMIWindow::spinROS);
    ros_timer_->start(10); // 10ms = ~100Hz
    
    // Make window fullscreen
    showFullScreen();


    orchestrator_timer_ = new QTimer(this);
    inspection_timer_ = new QTimer(this);
    safety_timer_ = new QTimer(this);

    connect(orchestrator_timer_, &QTimer::timeout, [this]() {
          setFrameBinaryState(ui->agentFrame, false);
        });

    setFrameBinaryState(ui->agentFrame, false);
    setFrameBinaryState(ui->inspectionFrame, false);
    setFrameBinaryState(ui->safetyFrame, false);

    orchestrator_sub_ = node_->create_subscription<std_msgs::msg::Header>(HardcodedConfig::OrchestratorHeartbeat, 10,
        [this](const std_msgs::msg::Header msg) {
          orchestrator_timer_->stop();
          setFrameBinaryState(ui->agentFrame, true);
          orchestrator_timer_->start(1000 / HardcodedConfig::OrchestratorHeartbeatFrequency);
        });
    

    // Agent vertical fill animation for system tiles (excluding CPU/GPU/NPU/RAM which are driven by /utilization)
    // agent_fill_timer_ = new QTimer(this);
    // connect(agent_fill_timer_, &QTimer::timeout, [this]() {
    //     agent_fill_percent_ += 5; // step 5%
    //     if (agent_fill_percent_ > 100) agent_fill_percent_ = 0; // wrap
    //     const int p = agent_fill_percent_;
    //     // Frames to update sequentially each tick
    //     const QList<QFrame*> frames = {
    //         ui->agentFrame,
    //         // cpu/gpu/npu/ram/nav2/moveit2 updated by /utilization subscriber
    //         ui->inspectionFrame,
    //         ui->safetyFrame
    //     };
    //     for (QFrame* frame : frames) {
    //     }
    // });
    // agent_fill_timer_->start(1000); // 1 Hz -> 1% per second
}

void HMIWindow::cameraButtonCallback(const std::string& cameraName) {
    // iterate buttons to set color for inactive one
    for (const auto& [name, button] : camera_buttons_) {
        if (name == cameraName) {
            button->setStyleSheet("background-color: green");
        } else {
            button->setStyleSheet("");
        }
    }
    auto topic = HardcodedConfig::CameraTopics.at(cameraName);
    RCLCPP_INFO(node_->get_logger(), "Subscribing to camera topic: %s", topic.c_str());
    // reset previous subscription
    image_sub_.reset();
    // Setup image subscription
    {
        rclcpp::QoS image_qos(rclcpp::KeepLast(5));
        image_qos.best_effort();
        image_qos.durability_volatile();
        image_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(
            topic, image_qos, [this](const sensor_msgs::msg::Image::SharedPtr msg)
            { imageCallback(msg, ui->graphicsViewCameras); });
    }

    // ensure top camera subscription exists
    if (!top_image_sub_) {
    {
        rclcpp::QoS top_qos(rclcpp::KeepLast(5));
        top_qos.best_effort();
        top_qos.durability_volatile();
        top_image_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(
            "/camera_image_color", top_qos, [this](const sensor_msgs::msg::Image::SharedPtr msg) {
                imageCallback(msg, ui->topCameraGraphicsView);
            });
    }
    }
}

HMIWindow::~HMIWindow()
{
    if (ros_timer_) {
        ros_timer_->stop();
    }
    rclcpp::shutdown();
    delete ui;
}

void HMIWindow::spinROS()
{
    rclcpp::spin_some(node_);
    updateRobotPose();
}

void HMIWindow::buildListTask(){
  queueView_->clear();
  LogItemWidget* tmpItem;
  for (const QString &item : past_steps_) {
    tmpItem = new LogItemWidget(QString(), QPixmap(), QColor(HardcodedConfig::Colors.at("PastSteps")), TextMode::Wrap, false, this);

    // currentTask_ = new LogItemWidget(QString(), QPixmap(), QColor("yellow"), TextMode::Wrap, false ,this);
    tmpItem->setText(item);
    queueView_->addItem(tmpItem);
  }
  for (const QString &item : task_queue_) {
    tmpItem = new LogItemWidget(QString(), QPixmap(), QColor(HardcodedConfig::Colors.at("TaskQueue")), TextMode::Wrap, false, this);
    tmpItem->setText(item);
    queueView_->addItem(tmpItem);
  }
}

void HMIWindow::imageCallback(const sensor_msgs::msg::Image::SharedPtr msg, QGraphicsView* view) {
    Q_ASSERT(view); // "GraphicsView is null";
    if (auto encoding = EncodingMap.find(msg->encoding); encoding != EncodingMap.end()) {
        QImage image(msg->data.data(), static_cast<int>(msg->width), static_cast<int>(msg->height), QImage::Format_RGBA8888);
        // Rotate top camera view 90 degrees left (counterclockwise)
        if (view == ui->topCameraGraphicsView) {
            QTransform rotateLeft;
            rotateLeft.rotate(-90.0); // counterclockwise
            image = image.transformed(rotateLeft);
        }
        if (!view->scene()) {
            view->setScene(new QGraphicsScene());
        }
        view->scene()->clear();
        view->scene()->addPixmap(QPixmap::fromImage(image));
        view->fitInView(view->scene()->itemsBoundingRect(), Qt::KeepAspectRatio);
    }
    else
    {
        RCLCPP_WARN(node_->get_logger(), "Unsupported image encoding: %s", msg->encoding.c_str());
    }
}

void HMIWindow::mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg)
{
    RCLCPP_INFO(node_->get_logger(), "Received map: %dx%d, resolution: %.3f", 
                msg->info.width, msg->info.height, msg->info.resolution);
    ui->graphicsViewMap->drawMap(msg);
    map_sub_.reset(); // unsubscribe after first map received
}

void HMIWindow::updateRobotPose()
{
    try {
        auto transform = tf_buffer_->lookupTransform("map", HardcodedConfig::RobotBaseFrame, tf2::TimePointZero);
        
        // Extract position and orientation
        float x = transform.transform.translation.x;
        float y = transform.transform.translation.y;
        
        // Convert quaternion to yaw angle
        auto& q = transform.transform.rotation;
        float theta = atan2(2.0 * (q.w * q.z + q.x * q.y), 
                           1.0 - 2.0 * (q.y * q.y + q.z * q.z));
        
        // Draw robot on map
        ui->graphicsViewMap->drawRobot(x, y, theta);
        
    } catch (tf2::TransformException &ex) {
        // Don't spam the log - transform might not be available yet
        static auto last_log_time = std::chrono::steady_clock::now();
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_log_time).count() >= 5) {
            RCLCPP_WARN(node_->get_logger(), "Could not transform map to base_link: %s", ex.what());
            last_log_time = now;
        }
    }
}

void HMIWindow::setFrameUtilization(QFrame* frame, float percent)
{
    if (!frame) return;
    // Clamp percent to [0,100]
    if (std::isnan(percent) || std::isinf(percent)) return;
    const double p = std::max(0.0, std::min(100.0, static_cast<double>(percent)));
    const QString fillColor = (p >= 80.0)
        ? "rgba(255,0,0,255)"
        : (p >= 50.0)
            ? "rgba(255,193,7,255)"
            : "rgba(76,175,80,255)";
    const QString style = QString(
        "QFrame#%1 { background: qlineargradient(x1:0, y1:1, x2:0, y2:0, "
        "stop:0 %2, "
        "stop:%3 %2, "
        "stop:%4 rgba(0,0,0,0), "
        "stop:1 rgba(0,0,0,0)); }")
        .arg(frame->objectName())
        .arg(fillColor)
        .arg(QString::number(p / 100.0, 'f', 2))
        .arg(QString::number(std::min(1.0, p / 100.0 + 0.001), 'f', 2));
    frame->setStyleSheet(style);
}

void HMIWindow::setFrameBinaryState(QFrame* frame, bool ok)
{
    if (!frame) return;
    const QString fillColor = ok ? "rgba(76,175,80,255)" : "rgba(255,0,0,255)";
    // 100% filled with the chosen color
    const QString style = QString(
        "QFrame#%1 { background: qlineargradient(x1:0, y1:1, x2:0, y2:0, "
        "stop:0 %2, stop:1 %2); }")
        .arg(frame->objectName())
        .arg(fillColor);
    frame->setStyleSheet(style);
}

void HMIWindow::setFrameDisabled(QFrame* frame)
{
    if (!frame) return;
    const QString style = QString(
        "QFrame#%1 { background: qlineargradient(x1:0, y1:1, x2:0, y2:0, "
        "stop:0 rgba(120,120,120,255), stop:1 rgba(120,120,120,255)); }")
        .arg(frame->objectName());
    frame->setStyleSheet(style);
}

void HMIWindow::logCallback(const rcl_interfaces::msg::Log::SharedPtr msg)
{
    const auto & logger_name = msg->name;
    if (HardcodedConfig::LogFilter.find(logger_name) == HardcodedConfig::LogFilter.end()) {
        return; // not in filter list
    }
    if (msg->level < HardcodedConfig::MinLogLevel)
    {
        return; // below min level
    }
    const char* level_names[] = {"DEBUG", "INFO", "WARN", "ERROR", "FATAL"};
    const char* level_name = (msg->level >= 10 && msg->level <= 50) ?
        level_names[(msg->level - 10) / 10] : "UNKNOWN";

    // Define colors based on log level
    QString color;
    switch (msg->level) {
        case 10: // DEBUG
            color = "#808080"; // Gray
            break;
        case 20: // INFO
            color = "#000000"; // Black
            break;
        case 30: // WARN
            color = "#FF8C00"; // Orange
            break;
        case 40: // ERROR
            color = "#FF0000"; // Red
            break;
        case 50: // FATAL
            color = "#8B0000"; // Dark Red
            break;
        default:
            color = "#000000"; // Black for unknown
            break;
    }

    auto msgLine = QString("[%1] [%2] %3: %4")
                       .arg(level_name)
                       .arg(QString::fromStdString(msg->name))
                       .arg(QString::fromStdString(msg->function))
                       .arg(QString::fromStdString(msg->msg));

    auto listItem = new QListWidgetItem(msgLine);
    listItem->setForeground(QColor(color));
    ui->listLog->insertItem(0, listItem);

    if (ui->listLog->count() > HardcodedConfig::MaxLogEntries) {
        delete ui->listLog->takeItem(ui->listLog->count() - 1);
    }
}

void HMIWindow::publishCmdVel(double linear_x, double angular_z)
{
    auto twist_msg = geometry_msgs::msg::Twist();
    twist_msg.linear.x = linear_x;
    twist_msg.angular.z = angular_z;
    cmd_vel_pub_->publish(twist_msg);
    RCLCPP_INFO(node_->get_logger(), "Published cmd_vel: linear.x=%.2f, angular.z=%.2f", linear_x, angular_z);
}

void HMIWindow::openCustomTaskDialog()
{
    TaskDialog dialog(this);
    if (dialog.exec() == QDialog::Accepted) {
        QString taskText = dialog.getTaskText();
        if (!taskText.isEmpty()) {
            RCLCPP_INFO(node_->get_logger(), "Publishing custom task: %s", taskText.toStdString().c_str());
            std_msgs::msg::String msg;
            msg.data = taskText.toStdString();
            user_prompt_pub_->publish(msg);
        }
    }
}

// void HMIWindow::setCurrentTaskName(const QString& name)
// {
//     if (!name.isEmpty()) {
//         const QString timestamp = QTime::currentTime().toString("HH:mm:ss");
//         const QString display = QString("%1: %2").arg(timestamp, name);
//         auto listItem = new QListWidgetItem(display);
//         listItem->setIcon(QIcon(":/icons/CurrentTask.svg")); // Use robot icon for current task
//         ui->listTask->insertItem(0, listItem);
//         ui->listTask->setCurrentItem(listItem);
//     }
// }
// 
// void HMIWindow::setDoneTasks(const QStringList& done)
// {
//     // Remove existing completed tasks (keep only current task at index 0)
//     while (ui->listTask->count() > 1) {
//         auto ptr = ui->listTask->takeItem(1);
//         if (ptr)
//         {
//             delete ptr;
//         }
//     }
// 
//     // Add completed tasks to the list (after current task)
//     for (const QString& taskName : done) {
//         auto listItem = new QListWidgetItem(taskName);
//         listItem->setIcon(QIcon(":/icons/DoneTask.svg")); // Use done icon for completed tasks
//         listItem->setForeground(QColor("#808080")); // Gray out completed tasks
//         ui->listTask->addItem(listItem);
//     }
// }


