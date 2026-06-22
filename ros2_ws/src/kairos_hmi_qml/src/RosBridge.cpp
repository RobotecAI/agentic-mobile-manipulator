// Copyright (C) 2025 Robotec.ai sp. z o.o. — Apache-2.0
#include "RosBridge.h"

#include <QMutexLocker>
#include <QPainter>
#include <QPainterPath>
#include <QTimer>
#include <algorithm>
#include <cmath>

namespace {
constexpr char kBaseCam[] = "/rgbd_camera/camera_image_color";
constexpr char kWristCam[] = "/wrist_camera/camera_image_color";
constexpr char kTopCam[] = "/camera_image_color";
constexpr char kRobotFrame[] = "egobase_link";
}  // namespace

RosBridge::RosBridge(QObject* parent) : QObject(parent)
{
    rclcpp::init(0, nullptr);
    node_ = rclcpp::Node::make_shared("kairos_hmi_qml");

    auto sensor_qos = rclcpp::SensorDataQoS();
    auto latched = rclcpp::QoS(1).transient_local();

    util_sub_ = node_->create_subscription<demo_msgs::msg::Utilization>(
        "/utilization", 10, [this](demo_msgs::msg::Utilization::SharedPtr m) {
            auto get = [&](const char* k) -> double {
                for (size_t i = 0; i < m->component_names.size() && i < m->component_values.size(); ++i)
                    if (m->component_names[i] == k) return m->component_values[i];
                return -1.0;
            };
            cpu_ = get("cpu"); ram_ = get("ram"); gpu_ = get("gpu");
            vram_ = get("vram"); disk_ = get("disk");
            nav2_ok_ = m->nav2_state; moveit2_ok_ = m->moveit2_state;
            has_telemetry_ = true;
            emit telemetryChanged();
        });

    hb_sub_ = node_->create_subscription<std_msgs::msg::Header>(
        "/orchestrator/heartbeat", 10, [this](std_msgs::msg::Header::SharedPtr) {
            last_hb_ = std::chrono::steady_clock::now();
            if (!agent_online_) { agent_online_ = true; emit agentOnlineChanged(); }
        });

    task_sub_ = node_->create_subscription<std_msgs::msg::String>(
        "/orchestrator/current_task", 10, [this](std_msgs::msg::String::SharedPtr m) {
            current_task_ = QString::fromStdString(m->data);
            emit currentTaskChanged();
        });
    past_sub_ = node_->create_subscription<std_msgs::msg::String>(
        "/agent/past_steps", 10, [this](std_msgs::msg::String::SharedPtr m) {
            past_steps_ = parseList(QString::fromStdString(m->data));
            emit planChanged();
        });
    queue_sub_ = node_->create_subscription<std_msgs::msg::String>(
        "/orchestrator/tasks_queue", 10, [this](std_msgs::msg::String::SharedPtr m) {
            task_queue_ = parseList(QString::fromStdString(m->data));
            emit planChanged();
        });

    action_sub_ = node_->create_subscription<rai_interfaces::msg::HRIMessage>(
        "/agent/current_action", 10, [this](rai_interfaces::msg::HRIMessage::SharedPtr m) {
            QString id = QString::fromStdString(m->communication_id);
            if (id != current_action_id_) {
                current_action_ = QString::fromStdString(m->text);
                current_action_id_ = id;
            } else {
                current_action_ += QString::fromStdString(m->text);
            }
            emit currentActionChanged();
        });

    vlm_sub_ = node_->create_subscription<demo_msgs::msg::VlmDescription>(
        "/vlm_topic", 10, [this](demo_msgs::msg::VlmDescription::SharedPtr m) {
            QVariantMap e;
            e["source"] = QString::fromStdString(m->source);
            e["description"] = QString::fromStdString(m->description);
            vlm_feed_.prepend(e);
            while (vlm_feed_.size() > 12) vlm_feed_.removeLast();
            emit vlmChanged();
        });

    log_sub_ = node_->create_subscription<rcl_interfaces::msg::Log>(
        "/rosout", rclcpp::QoS(50), [this](rcl_interfaces::msg::Log::SharedPtr m) {
            if (m->level < 20) return;  // INFO and above
            QVariantMap e;
            e["level"] = static_cast<int>(m->level);
            e["name"] = QString::fromStdString(m->name);
            e["msg"] = QString::fromStdString(m->msg);
            events_.prepend(e);
            while (events_.size() > 40) events_.removeLast();
            emit eventsChanged();
        });

    map_sub_ = node_->create_subscription<nav_msgs::msg::OccupancyGrid>(
        "/global_costmap/static_layer", latched, [this](nav_msgs::msg::OccupancyGrid::SharedPtr m) {
            { QMutexLocker lk(&img_mutex_); map_ = m; }
            ++map_rev_; emit mapChanged();
        });
    plan_sub_ = node_->create_subscription<nav_msgs::msg::Path>(
        "/plan", 10, [this](nav_msgs::msg::Path::SharedPtr m) {
            { QMutexLocker lk(&img_mutex_); plan_ = m; }
            ++map_rev_; emit mapChanged();
        });

    auto cam_cb = [this](const QString& name) {
        return [this, name](sensor_msgs::msg::Image::SharedPtr m) {
            QImage img = toQImage(*m);
            { QMutexLocker lk(&img_mutex_); camera_images_[name] = img; }
            ++camera_rev_;
            emit cameraChanged();
        };
    };
    base_cam_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(kBaseCam, sensor_qos, cam_cb("base"));
    wrist_cam_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(kWristCam, sensor_qos, cam_cb("wrist"));
    top_cam_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(kTopCam, sensor_qos, cam_cb("top"));

    prompt_pub_ = node_->create_publisher<std_msgs::msg::String>("/user_tasks", 10);
    stop_pub_ = node_->create_publisher<std_msgs::msg::String>("/emergency_stop", 10);
    cmd_vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
    restart_cli_ = node_->create_client<std_srvs::srv::Trigger>("/restart");
    standard_cli_ = node_->create_client<std_srvs::srv::Trigger>("/rai/scene/standard");
    housekeep_cli_ = node_->create_client<std_srvs::srv::Trigger>("/rai/scene/housekeep");
    anomalies_cli_ = node_->create_client<std_srvs::srv::Trigger>("/rai/scene/anomalies");
    cleanup_cli_ = node_->create_client<std_srvs::srv::Trigger>("/rai/scene/cleanup");

    tf_buffer_ = std::make_unique<tf2_ros::Buffer>(node_->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    spin_timer_ = new QTimer(this);
    connect(spin_timer_, &QTimer::timeout, this, &RosBridge::spin);
    spin_timer_->start(10);

    hb_timer_ = new QTimer(this);
    connect(hb_timer_, &QTimer::timeout, this, &RosBridge::checkHeartbeat);
    hb_timer_->start(1000);
}

RosBridge::~RosBridge()
{
    if (spin_timer_) spin_timer_->stop();
    rclcpp::shutdown();
}

void RosBridge::spin() { rclcpp::spin_some(node_); }

void RosBridge::checkHeartbeat()
{
    if (!agent_online_) return;
    auto age = std::chrono::steady_clock::now() - last_hb_;
    if (std::chrono::duration_cast<std::chrono::milliseconds>(age).count() > 4000) {
        agent_online_ = false;
        emit agentOnlineChanged();
    }
}

void RosBridge::sendPrompt(const QString& text)
{
    if (text.trimmed().isEmpty()) return;
    std_msgs::msg::String m; m.data = text.toStdString();
    prompt_pub_->publish(m);
}

void RosBridge::estop()
{
    stop_pub_->publish(std_msgs::msg::String());
}

void RosBridge::teleop(double linear, double angular)
{
    geometry_msgs::msg::Twist t; t.linear.x = linear; t.angular.z = angular;
    cmd_vel_pub_->publish(t);
}

void RosBridge::restart() { callTrigger(restart_cli_, "restart"); }

void RosBridge::runScenario(const QString& key)
{
    if (key == "standard") callTrigger(standard_cli_, key);
    else if (key == "housekeep") callTrigger(housekeep_cli_, key);
    else if (key == "anomalies") callTrigger(anomalies_cli_, key);
    else if (key == "cleanup") callTrigger(cleanup_cli_, key);
}

void RosBridge::callTrigger(rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr client, const QString& label)
{
    if (!client->service_is_ready()) {
        RCLCPP_WARN(node_->get_logger(), "service %s not ready", label.toStdString().c_str());
        return;
    }
    auto req = std::make_shared<std_srvs::srv::Trigger::Request>();
    client->async_send_request(req);  // fire and forget; spun on GUI thread
}

QStringList RosBridge::parseList(const QString& raw)
{
    QStringList out;
    QString s = raw.trimmed();
    if (s.startsWith('[') && s.endsWith(']')) s = s.mid(1, s.length() - 2);
    if (s.trimmed().isEmpty()) return out;
    for (QString item : s.split('|')) {
        item = item.trimmed();
        if ((item.startsWith('"') && item.endsWith('"')) || (item.startsWith('\'') && item.endsWith('\'')))
            item = item.mid(1, item.length() - 2);
        if (!item.isEmpty()) out << item;
    }
    return out;
}

QImage RosBridge::toQImage(const sensor_msgs::msg::Image& m)
{
    const int w = static_cast<int>(m.width), h = static_cast<int>(m.height);
    if (w <= 0 || h <= 0) return {};
    const uchar* d = m.data.data();
    if (m.encoding == "rgb8")
        return QImage(d, w, h, static_cast<int>(m.step), QImage::Format_RGB888).copy();
    if (m.encoding == "bgr8")
        return QImage(d, w, h, static_cast<int>(m.step), QImage::Format_RGB888).rgbSwapped();
    if (m.encoding == "rgba8")
        return QImage(d, w, h, static_cast<int>(m.step), QImage::Format_RGBA8888).copy();
    if (m.encoding == "bgra8")
        return QImage(d, w, h, static_cast<int>(m.step), QImage::Format_RGBA8888).rgbSwapped();
    if (m.encoding == "mono8")
        return QImage(d, w, h, static_cast<int>(m.step), QImage::Format_Grayscale8).copy();
    return {};
}

QImage RosBridge::cameraImage(const QString& name) const
{
    QMutexLocker lk(&img_mutex_);
    return camera_images_.value(name);
}

QImage RosBridge::mapImage() const
{
    // snapshot the shared pointers under lock, then render without holding it
    nav_msgs::msg::OccupancyGrid::SharedPtr map;
    nav_msgs::msg::Path::SharedPtr plan;
    {
        QMutexLocker lk(&img_mutex_);
        map = map_;
        plan = plan_;
    }

    const int W = 720, H = 720;
    QImage img(W, H, QImage::Format_ARGB32_Premultiplied);
    img.fill(QColor("#0a1018"));
    if (!map || map->info.width == 0) return img;

    const int gw = static_cast<int>(map->info.width);
    const int gh = static_cast<int>(map->info.height);
    const double res = map->info.resolution;
    const double ox = map->info.origin.position.x;
    const double oy = map->info.origin.position.y;

    // rasterise grid (flip Y: ROS origin is bottom-left)
    QImage cells(gw, gh, QImage::Format_ARGB32);
    for (int my = 0; my < gh; ++my)
        for (int mx = 0; mx < gw; ++mx) {
            int v = map->data[my * gw + mx];
            QColor c = (v == 0) ? QColor(20, 32, 50) : (v >= 50) ? QColor(70, 150, 195) : QColor(12, 16, 24);
            cells.setPixelColor(mx, gh - 1 - my, c);
        }

    QPainter p(&img);
    p.setRenderHint(QPainter::Antialiasing, true);
    const double scale = std::min(double(W) / gw, double(H) / gh);
    const double drawW = gw * scale, drawH = gh * scale;
    const double offX = (W - drawW) / 2.0, offY = (H - drawH) / 2.0;
    p.drawImage(QRectF(offX, offY, drawW, drawH), cells);

    auto toPx = [&](double wx, double wy) {
        double gx = (wx - ox) / res, gy = (wy - oy) / res;
        return QPointF(offX + gx * scale, offY + (gh - gy) * scale);
    };

    if (plan && plan->poses.size() > 1) {
        QPainterPath path;
        bool first = true;
        for (const auto& ps : plan->poses) {
            QPointF pt = toPx(ps.pose.position.x, ps.pose.position.y);
            if (first) { path.moveTo(pt); first = false; } else path.lineTo(pt);
        }
        p.setBrush(Qt::NoBrush);
        p.setPen(QPen(QColor(34, 211, 238, 70), 9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));  // glow
        p.drawPath(path);
        p.setPen(QPen(QColor(34, 211, 238), 2.6, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.drawPath(path);
        QPointF head = toPx(plan->poses.back().pose.position.x, plan->poses.back().pose.position.y);
        p.setBrush(QColor(34, 211, 238));
        p.setPen(QPen(QColor(234, 253, 255), 1.5));
        p.drawEllipse(head, 5, 5);
    }

    // robot pose from TF
    try {
        auto tf = tf_buffer_->lookupTransform("map", kRobotFrame, tf2::TimePointZero);
        QPointF rp = toPx(tf.transform.translation.x, tf.transform.translation.y);
        p.setBrush(QColor(167, 139, 250));
        p.setPen(QPen(QColor(255, 255, 255), 1.5));
        p.drawEllipse(rp, 6, 6);
    } catch (...) {
    }
    return img;
}
