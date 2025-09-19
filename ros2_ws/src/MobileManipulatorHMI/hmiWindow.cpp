#include "hmiWindow.h"
#include "./ui_hmiWindow.h"
#include <tf2/exceptions.h>
#include <chrono>
#include <cmath>
#include <QMessageBox>

void CallService(QWidget *parent, rclcpp::Node::SharedPtr &node, rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr& client)
{
    const bool ok = client->wait_for_service(std::chrono::seconds(1));
    if (!ok) {
        QMessageBox::warning(parent, "Service Call Failed", "Service not available.");
        return;
    }
    auto request = std::make_shared<std_srvs::srv::Trigger::Request>();
    auto result_future = client->async_send_request(request);
    // Wait for the result.
    if (rclcpp::spin_until_future_complete(node, result_future) !=
        rclcpp::FutureReturnCode::SUCCESS)
    {
        QMessageBox::warning(parent, "Service Call Failed", "Failed to call service.");
        return;
    }
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

    // create cameras buttons and assign callback
    for (const auto& [name, topic] : HardcodedConfig::CameraTopics) {
        auto button = new QPushButton(name.c_str(), this);
        camera_buttons_[name] = button;
        ui->groupBoxCamera->layout()->addWidget(button);
        button->connect(button, &QPushButton::clicked, [this, name]() {
            cameraButtonCallback(name);
        });
    }

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

    task_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::TaskTopic, 10);

    user_prompt_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::UserPromptTopic, 10);

    assert(ui->tableWidgetUtilization->rowCount() >= 3);
    resource_sub_ = node_->create_subscription<std_msgs::msg::Float32MultiArray>(
        HardcodedConfig::ResourceTopics, 10,
        [this](const std_msgs::msg::Float32MultiArray::SharedPtr msg) {
            if (msg->data.size() >= 3) {
                const float cpu = msg->data[0];
                const float gpu = msg->data[1];
                const float ram = msg->data[2];
                ui->tableWidgetUtilization->item(0, 0)->setText(QString::number(cpu, 'f', 1) + " %");
                ui->tableWidgetUtilization->item(1, 0)->setText(QString::number(gpu, 'f', 1) + " %");
                ui->tableWidgetUtilization->item(2, 0)->setText(QString::number(ram, 'f', 1) + " %");
            }
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

    // connect teleop buttons
    for (auto button : {ui->pushButtonTeleopFw, ui->pushButtonTeleopBk, ui->pushButtonTeleopLeft, ui->pushButtonTeleopRight}) {
        connect(button, &QPushButton::released, [this]() { publishCmdVel(0.0, 0.0); });
    }

    // create task buttons
    for (const auto& [name, task] : HardcodedConfig::Tasks) {
        auto button = new QPushButton(name.c_str(), this);
        ui->groupBoxPredefinedTasks->layout()->addWidget(button);
        button->connect(button, &QPushButton::clicked, [this, task]() {
            RCLCPP_INFO(node_->get_logger(), "Publishing task: %s", task.c_str());
            std_msgs::msg::String msg;
            msg.data = task;
            task_pub_->publish(msg);
        });
    }

    // create custom task button
    auto customTaskButton = new QPushButton("...", this);
    customTaskButton->setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }");
    ui->groupBoxPredefinedTasks->layout()->addWidget(customTaskButton);
    connect(customTaskButton, &QPushButton::clicked, this, &HMIWindow::openCustomTaskDialog);

    // Enable zooming on graphics views
    ui->graphicsViewMap->setDragMode(QGraphicsView::RubberBandDrag);
    ui->graphicsViewMap->setRenderHint(QPainter::Antialiasing);
    ui->graphicsViewMap->setTransformationAnchor(QGraphicsView::AnchorUnderMouse);

    // clients for services
    emergency_stop_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::EmergencyStopService);
    restart_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::Restart);

    // buttons
    connect(ui->StopButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, emergency_stop_srv_);
    });
    connect(ui->RestartButton, &QPushButton::clicked, [this]() {
        CallService(this, node_, restart_srv_);
    });

    // done tasks and current task subscribers
    currenttask_sub_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::AgentCurrentStep, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            setCurrentTaskName(msg->data.c_str());
        });
    donetasks_sub_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::AgentTotalSteps, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            // list is Python list style : [ "task1", "task2", ...]
            // we convert to QStringList by removing brackets and splitting by comma
            QStringList done;

            QString listStr = QString::fromStdString(msg->data);
            listStr = listStr.trimmed();

            // Remove brackets [ ]
            if (listStr.startsWith('[') && listStr.endsWith(']')) {
                listStr = listStr.mid(1, listStr.length() - 2);
            }

            // Split by comma and clean up each item
            if (!listStr.isEmpty()) {
                QStringList rawItems = listStr.split(',');
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
            setDoneTasks(done);
        });

    // Setup ROS spinning timer
    ros_timer_ = new QTimer(this);
    connect(ros_timer_, &QTimer::timeout, this, &HMIWindow::spinROS);
    ros_timer_->start(10); // 10ms = ~100Hz
    
    // Make window fullscreen
    showFullScreen();
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
    image_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(
        topic, 10,[this](const sensor_msgs::msg::Image::SharedPtr msg)
        {imageCallback(msg, ui->graphicsViewCameras); });
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

const std::unordered_map<std::string, int> EncodingMap = {
    {"mono8", QImage::Format_Grayscale8},
    {"rgb8", QImage::Format_RGB888},
    {"rgba8", QImage::Format_RGBA8888},
    {"bgra8", QImage::Format_RGBA8888}, // Will need to swap channels
    // Add more mappings as needed
};

void HMIWindow::imageCallback(const sensor_msgs::msg::Image::SharedPtr msg, QGraphicsView* view) {
    Q_ASSERT(view); // "GraphicsView is null";
    if (auto enconding = EncodingMap.find(msg->encoding); enconding != EncodingMap.end()) {
        QImage image(msg->data.data(), static_cast<int>(msg->width), static_cast<int>(msg->height), QImage::Format_RGBA8888);
        if (!view->scene()) {
            view->setScene(new QGraphicsScene());
        }
        view->scene()->clear();
        view->scene()->addPixmap(QPixmap::fromImage(image));
        view->fitInView(ui->graphicsViewCameras->scene()->itemsBoundingRect(), Qt::KeepAspectRatio);
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

void HMIWindow::setCurrentTaskName(const QString& name)
{
    // Remove existing current task (index 0)
    if (ui->listTask->count() > 0)
    {
        auto ptr = ui->listTask->item(0);
        if (ptr)
        {
            delete ptr;
        }
    }
    // Add current task with appropriate icon
    if (!name.isEmpty()) {
        auto listItem = new QListWidgetItem(name);
        listItem->setIcon(QIcon(":/icons/CurrentTask.svg")); // Use robot icon for current task
        ui->listTask->insertItem(0, listItem);
        ui->listTask->setCurrentItem(listItem);
    }
}

void HMIWindow::setDoneTasks(const QStringList& done)
{
    // Remove existing completed tasks (keep only current task at index 0)
    while (ui->listTask->count() > 1) {
        auto ptr = ui->listTask->takeItem(1);
        if (ptr)
        {
            delete ptr;
        }
    }

    // Add completed tasks to the list (after current task)
    for (const QString& taskName : done) {
        auto listItem = new QListWidgetItem(taskName);
        listItem->setIcon(QIcon(":/icons/DoneTask.svg")); // Use done icon for completed tasks
        listItem->setForeground(QColor("#808080")); // Gray out completed tasks
        ui->listTask->addItem(listItem);
    }
}


