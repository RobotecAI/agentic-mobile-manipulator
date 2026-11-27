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

#include "RosBridge.h"

#include <QDateTime>
#include <QElapsedTimer>
#include <QNetworkReply>
#include <QTime>
#include <QUrl>

#include <cmath>
#include <nlohmann/json.hpp>

#include "ModelConfig.h"
#include "ParseRaiData.h"

namespace {

const char *kTaskTopic = "/user_tasks";
const char *kEstopTopic = "/emergency_stop";
const char *kReleaseTopic = "/emergency_release";
const char *kEstopStateTopic = "/orchestrator/estop";
const char *kEventsTopic = "/agent/events";
const char *kActionTopic = "/agent/current_action";
const char *kPastStepsTopic = "/agent/past_steps";
const char *kCurrentTaskTopic = "/orchestrator/current_task";
const char *kQueueTopic = "/orchestrator/tasks_queue";
const char *kOrchestratorHeartbeat = "/orchestrator/heartbeat";
const char *kAgentsHeartbeat = "/agents/heartbeat";
const char *kVlmTopic = "/vlm_topic";
const char *kUtilizationTopic = "/utilization";
const char *kMapTopic = "/global_costmap/static_layer";
const char *kPathTopic = "/plan";
const char *kGoalTopic = "/goal_pose";
const char *kCmdVelTopic = "/cmd_vel";
const char *kRobotFrame = "egobase_link";

struct Camera { const char *label; const char *topic; bool rotate; };
const Camera kCameras[] = {
    {"Base", "/rgbd_camera/camera_image_color", false},
    {"Wrist", "/wrist_camera/camera_image_color", false},
    {"Top", "/camera_image_color", true},
};

// Agents shown on the Agents page: name -> heartbeat key on /agents/heartbeat
// (frame_id), group, color. Executors run inside the orchestrator process.
struct AgentInfo { const char *name; const char *key; const char *group; const char *color; };
const AgentInfo kAgents[] = {
    {"Orchestrator", "orchestrator", "orchestrator", "#5B9DFF"},
    {"Housekeep", "", "executor", "#7FC8FF"},
    {"Package movement", "", "executor", "#B08CFF"},
    {"Image analysis", "", "executor", "#C7D35B"},
    {"Inspection", "inspection", "background", "#FF9F43"},
    {"Safety", "safety", "background", "#FF6B81"},
    {"Nav2", "nav2", "skill", "#3CC6B8"},
    {"MoveIt2", "moveit2", "skill", "#E0A8FF"},
    {"Scene", "scene", "skill", "#D7DE7A"},
};

constexpr qint64 kHeartbeatStaleMs = 12000;
constexpr qint64 kActiveWindowMs = 6000;
constexpr int kMaxLogs = 300;
constexpr int kMaxHistory = 60;
constexpr int kMaxVlmImages = 50;

QString shortTokens(qint64 n)
{
    return n >= 1000 ? QString::number(n / 1000.0, 'f', 1) + "k" : QString::number(n);
}

QString prettyJson(const nlohmann::json &j)
{
    if (j.is_string()) {
        return QString::fromStdString(j.get<std::string>());
    }
    return QString::fromStdString(j.dump(2));
}

// sensor_msgs/Image -> QImage (deep copy); null for unsupported encodings.
QImage toQImage(const sensor_msgs::msg::Image &msg)
{
    const auto *data = msg.data.data();
    const int w = static_cast<int>(msg.width), h = static_cast<int>(msg.height), step = static_cast<int>(msg.step);
    if (msg.data.size() < static_cast<size_t>(step) * static_cast<size_t>(h) || w <= 0 || h <= 0) return {};
    if (msg.encoding == "rgb8") return QImage(data, w, h, step, QImage::Format_RGB888).copy();
    if (msg.encoding == "bgr8") return QImage(data, w, h, step, QImage::Format_RGB888).rgbSwapped();
    if (msg.encoding == "rgba8") return QImage(data, w, h, step, QImage::Format_RGBA8888).copy();
    if (msg.encoding == "bgra8") return QImage(data, w, h, step, QImage::Format_ARGB32).copy();
    if (msg.encoding == "mono8") return QImage(data, w, h, step, QImage::Format_Grayscale8).copy();
    return {};
}

QString firstLine(const QString &text, int max = 90)
{
    QString line = text.section('\n', 0, 0).trimmed();
    return line.size() > max ? line.left(max - 1) + "…" : line;
}

}  // namespace

RosBridge::RosBridge(RosImageProvider *images, QObject *parent)
    : QObject(parent), images_(images), events_(new AgentEventModel(this)),
      streamFilter_(new AgentFilterModel(this)), traceFilter_(new AgentFilterModel(this))
{
    streamFilter_->setSourceModel(events_);
    traceFilter_->setSourceModel(events_);
    resources_ = {{"CPU", -1, {}}, {"GPU", -1, {}}, {"NPU", -1, {}}, {"RAM", -1, {}}};
    node_ = rclcpp::Node::make_shared("hmi");
    const ModelNames models = loadModelNames(defaultModelConfigPath());
    llmModel_ = models.llm;

    taskPub_ = node_->create_publisher<std_msgs::msg::String>(kTaskTopic, 10);
    estopPub_ = node_->create_publisher<std_msgs::msg::Empty>(kEstopTopic, 10);
    releasePub_ = node_->create_publisher<std_msgs::msg::Empty>(kReleaseTopic, 10);
    cmdVelPub_ = node_->create_publisher<geometry_msgs::msg::Twist>(kCmdVelTopic, 10);
    goalPub_ = node_->create_publisher<geometry_msgs::msg::PoseStamped>(kGoalTopic, 10);
    for (const char *scene : {"standard", "housekeep", "anomalies", "cleanup"}) {
        sceneClients_[scene] = node_->create_client<std_srvs::srv::Trigger>(std::string("/rai/scene/") + scene);
    }

    subs_.push_back(node_->create_subscription<rosgraph_msgs::msg::Clock>(
        "/clock", rclcpp::QoS(10).best_effort(), [this](const rosgraph_msgs::msg::Clock &msg) {
            const QString t = QTime(0, 0).addSecs(static_cast<int>(msg.clock.sec)).toString("HH:mm:ss");
            if (t != simTime_) {
                simTime_ = t;
                emit simTimeChanged();
            }
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::Bool>(
        kEstopStateTopic, 10, [this](const std_msgs::msg::Bool &msg) {
            if (msg.data != estopped_) {
                estopped_ = msg.data;
                emit estopChanged();
            }
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::String>(
        kEventsTopic, 100, [this](const std_msgs::msg::String &msg) { onEvent(msg.data); }));
    subs_.push_back(node_->create_subscription<rai_interfaces::msg::HRIMessage>(
        kActionTopic, 100, [this](const rai_interfaces::msg::HRIMessage &msg) { onAction(msg); }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::String>(
        kPastStepsTopic, 10, [this](const std_msgs::msg::String &msg) {
            // A Python list repr or "a|b|c".
            QString list = QString::fromStdString(msg.data).trimmed();
            if (list.startsWith('[') && list.endsWith(']')) {
                list = list.mid(1, list.size() - 2);
            }
            QStringList steps;
            for (QString item : list.split(list.contains('|') ? "|" : "', '")) {
                item = item.trimmed();
                while (item.startsWith('\'') || item.startsWith('"')) item.remove(0, 1);
                while (item.endsWith('\'') || item.endsWith('"')) item.chop(1);
                if (!item.isEmpty()) steps << item;
            }
            if (steps != pastSteps_) {
                pastSteps_ = steps;
                emit tasksChanged();
            }
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::String>(
        kCurrentTaskTopic, 10, [this](const std_msgs::msg::String &msg) {
            QString task = QString::fromStdString(msg.data);
            setCurrentTask(task.startsWith("No task currently") ? QString() : task);
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::String>(
        kQueueTopic, 10, [this](const std_msgs::msg::String &msg) {
            const QStringList queue = QString::fromStdString(msg.data).split('|', Qt::SkipEmptyParts);
            if (queue != queue_) {
                queue_ = queue;
                emit tasksChanged();
            }
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::Header>(
        kOrchestratorHeartbeat, 10, [this](const std_msgs::msg::Header &) {
            agentStates_["Orchestrator"].heartbeatMs = events_->nowMs();
        }));
    subs_.push_back(node_->create_subscription<std_msgs::msg::Header>(
        kAgentsHeartbeat, 50, [this](const std_msgs::msg::Header &msg) {
            const QString key = QString::fromStdString(msg.frame_id);
            for (const auto &a : kAgents) {
                if (key == a.key) {
                    agentStates_[a.name].heartbeatMs = events_->nowMs();
                }
            }
        }));
    subs_.push_back(node_->create_subscription<demo_msgs::msg::VlmDescription>(
        kVlmTopic, 10, [this](const demo_msgs::msg::VlmDescription &msg) { onVlm(msg); }));
    subs_.push_back(node_->create_subscription<demo_msgs::msg::Utilization>(
        kUtilizationTopic, 10, [this](const demo_msgs::msg::Utilization &msg) {
            const size_t n = std::min(msg.component_names.size(), msg.component_values.size());
            for (size_t i = 0; i < n; ++i) {
                const QString name = QString::fromStdString(msg.component_names[i]).toUpper();
                for (Resource &r : resources_) {
                    if (r.name == name) {
                        r.value = msg.component_values[i];
                        r.history.append(r.value < 0 ? 0.0 : static_cast<double>(r.value));
                        while (r.history.size() > kMaxHistory) r.history.removeFirst();
                    }
                }
            }
            nav2Ok_ = msg.nav2_state;
            moveit2Ok_ = msg.moveit2_state;
            utilizationMs_ = events_->nowMs();
            emit resourcesChanged();
        }));
    subs_.push_back(node_->create_subscription<rcl_interfaces::msg::Log>(
        "/rosout", rclcpp::QoS(200), [this](const rcl_interfaces::msg::Log &msg) { onLog(msg); }));
    subs_.push_back(node_->create_subscription<nav_msgs::msg::OccupancyGrid>(
        kMapTopic, rclcpp::QoS(1).transient_local(), [this](const nav_msgs::msg::OccupancyGrid &msg) { onMap(msg); }));
    subs_.push_back(node_->create_subscription<nav_msgs::msg::Path>(
        kPathTopic, 10, [this](const nav_msgs::msg::Path &msg) { onPath(msg); }));
    {
        rclcpp::QoS qos(rclcpp::KeepLast(2));
        qos.best_effort();
        const Camera &top = kCameras[2];
        subs_.push_back(node_->create_subscription<sensor_msgs::msg::Image>(
            top.topic, qos, [this](const sensor_msgs::msg::Image &msg) { onImage(msg, "top", true); }));
    }
    subscribeCamera();

    tfBuffer_ = std::make_unique<tf2_ros::Buffer>(node_->get_clock());
    tfListener_ = std::make_shared<tf2_ros::TransformListener>(*tfBuffer_);

    for (const Endpoint &e : loadEndpoints(defaultModelConfigPath())) {
        endpoints_.append(QVariantMap{{"name", e.name}, {"model", e.model}, {"backend", e.backend.toUpper()},
                                      {"type", e.type}, {"host", e.host}, {"port", e.port},
                                      {"ok", false}, {"checked", false}, {"latencyMs", -1}});
    }

    connect(&spinTimer_, &QTimer::timeout, this, &RosBridge::spin);
    spinTimer_.start(10);
    connect(&secondTimer_, &QTimer::timeout, this, [this]() {
        events_->refreshStreaming();
        if (logsDirty_) {
            logsDirty_ = false;
            emit logsChanged();
        }
        emit tick();
    });
    secondTimer_.start(500);
    connect(&endpointTimer_, &QTimer::timeout, this, &RosBridge::pollEndpoints);
    endpointTimer_.start(5000);
    QTimer::singleShot(500, this, &RosBridge::pollEndpoints);
}

RosBridge::~RosBridge()
{
    spinTimer_.stop();
    cameraSub_.reset();
    subs_.clear();
    node_.reset();
}

void RosBridge::spin()
{
    if (!rclcpp::ok()) {
        return;
    }
    rclcpp::spin_some(node_);
    static QElapsedTimer poseClock;
    if (!poseClock.isValid() || poseClock.elapsed() > 100) {
        poseClock.restart();
        updatePose();
    }
}

// ─── Agent stream ─────────────────────────────────────────────────────────────

QString RosBridge::agentForNode(const QString &node)
{
    static const QHash<QString, QString> names = {
        {"megamind", "Orchestrator"}, {"housekeep", "Housekeep"},
        {"package_movement", "Package movement"}, {"image_analysis", "Image analysis"},
    };
    if (names.contains(node)) {
        return names.value(node);
    }
    QString name = node;
    name.replace('_', ' ');
    return name.isEmpty() ? QStringLiteral("Orchestrator") : name.left(1).toUpper() + name.mid(1);
}

QString RosBridge::agentColor(const QString &agent) const
{
    for (const auto &a : kAgents) {
        if (agent == a.name) {
            return a.color;
        }
    }
    return "#9AA4B2";
}

void RosBridge::markActive(const QString &agent, const QString &doing)
{
    AgentState &s = agentStates_[agent];
    s.activeMs = events_->nowMs();
    if (!doing.isEmpty()) {
        s.doing = firstLine(doing);
    }
}

void RosBridge::setCurrentTask(const QString &task)
{
    if (task == currentTask_) {
        return;
    }
    currentTask_ = task;
    taskStartMs_ = events_->nowMs();
    emit tasksChanged();
}

// /agent/events: one JSON object per message (contract in docs/setup_hmi.md).
void RosBridge::onEvent(const std::string &json)
{
    const auto j = nlohmann::json::parse(json, nullptr, false);
    if (!j.is_object() || !j.contains("type")) {
        return;
    }
    eventsSeen_ = true;
    auto str = [&j](const char *key) {
        return j.contains(key) && j[key].is_string() ? QString::fromStdString(j[key].get<std::string>()) : QString();
    };
    const QString type = str("type");
    const QString node = str("node");
    const QString runId = str("run_id");
    const QString agent = agentForNode(node);

    if (type == "task_start") {
        setCurrentTask(str("task"));
        AgentEvent e;
        e.agent = "Orchestrator";
        e.kind = "task";
        e.text = "Task started: " + str("task");
        e.task = currentTask_;
        events_->addEvent(e);
    } else if (type == "task_end") {
        AgentEvent e;
        e.agent = "Orchestrator";
        e.kind = "task";
        e.text = QString("Task %1: %2").arg(str("status").isEmpty() ? "finished" : str("status"), str("task"));
        e.task = str("task");
        events_->addEvent(e);
    } else if (type == "text" || type == "thinking") {
        const QString chunk = str("chunk");
        events_->appendChunk(node + ":" + runId, agent, node, type, chunk, currentTask_);
        markActive(agent, type == "text" ? chunk : QString("thinking…"));
    } else if (type == "tool_start") {
        AgentEvent e;
        e.agent = agent;
        e.node = node;
        e.commId = "tool:" + runId;
        e.kind = "tool";
        e.toolName = str("tool");
        e.text = j.contains("args") ? prettyJson(j["args"]) : QString();
        e.status = "running";
        e.task = currentTask_;
        events_->addEvent(e);
        markActive(agent, e.toolName);
    } else if (type == "tool_end") {
        const QString status = str("status").isEmpty() ? "ok" : str("status");
        const QString output = j.contains("output") ? prettyJson(j["output"]) : QString();
        const qint64 now = events_->nowMs();
        events_->update("tool:" + runId, [&](AgentEvent &e) {
            e.status = status;
            e.result = output;
            e.endMs = now;
        });
    } else if (type == "llm_end") {
        const qint64 in = j.value("tokens_in", 0);
        const qint64 out = j.value("tokens_out", 0);
        if (in || out) {
            const QString tokens = QString("%1 in · %2 out").arg(shortTokens(in), shortTokens(out));
            events_->updateLastOfNode(node, [&](AgentEvent &e) { e.tokens = tokens; });
        }
    } else if (type == "steps") {
        QStringList steps;
        if (j.contains("steps") && j["steps"].is_array()) {
            for (const auto &s : j["steps"]) {
                if (s.is_string()) steps << QString::fromStdString(s.get<std::string>());
            }
        }
        if (steps != pastSteps_) {
            pastSteps_ = steps;
            emit tasksChanged();
        }
    }
}

// Legacy stream, used until the first /agent/events message arrives.
void RosBridge::onAction(const rai_interfaces::msg::HRIMessage &msg)
{
    if (eventsSeen_) {
        return;
    }
    const QString commId = QString::fromStdString(msg.communication_id);
    const QString node = commId.section(':', 0, 0);
    const QString agent = agentForNode(node);
    const QString text = QString::fromStdString(msg.text);
    if (const auto parsed = ParseRaiData::parseHRIMessage(text); parsed && parsed->type_ == "tool_call") {
        AgentEvent e;
        e.agent = agent;
        e.node = node;
        e.commId = "tool:" + commId + ":" + QString::number(events_->nowMs());
        e.kind = "tool";
        e.toolName = parsed->tool_name_;
        QStringList args;
        for (auto it = parsed->parameters_.cbegin(); it != parsed->parameters_.cend(); ++it) {
            args << QString("%1: %2").arg(it.key(), it.value());
        }
        e.text = args.join('\n');
        e.task = currentTask_;
        events_->addEvent(e);
        markActive(agent, e.toolName);
        return;
    }
    events_->appendChunk(commId, agent, node, "text", text, currentTask_);
    markActive(agent, text);
}

void RosBridge::onVlm(const demo_msgs::msg::VlmDescription &msg)
{
    const QString source = QString::fromStdString(msg.source);
    AgentEvent e;
    e.agent = source.isEmpty() ? QString("Inspection") : source;
    e.kind = "vlm";
    e.text = QString::fromStdString(msg.description);
    e.task = currentTask_;
    const QImage image = toQImage(msg.image);
    if (!image.isNull()) {
        e.image = QString("vlm/%1").arg(vlmCounter_);
        images_->setImage(e.image, image);
        images_->remove(QString("vlm/%1").arg(vlmCounter_ - kMaxVlmImages));
        ++vlmCounter_;
    }
    events_->addEvent(e);
    markActive(e.agent, e.text);
}

// ─── Logs, images, map ────────────────────────────────────────────────────────

void RosBridge::onLog(const rcl_interfaces::msg::Log &msg)
{
    static const QHash<int, QString> levels = {{10, "DEBUG"}, {20, "INFO"}, {30, "WARN"}, {40, "ERROR"}, {50, "FATAL"}};
    const QString time = QDateTime::fromSecsSinceEpoch(msg.stamp.sec).toString("HH:mm:ss");
    logs_.prepend(QVariantMap{{"t", time}, {"level", levels.value(msg.level, "INFO")},
                              {"node", QString::fromStdString(msg.name)}, {"msg", QString::fromStdString(msg.msg)}});
    while (logs_.size() > kMaxLogs) logs_.removeLast();
    logsDirty_ = true;
}

void RosBridge::onImage(const sensor_msgs::msg::Image &msg, const QString &id, bool rotate)
{
    const qint64 now = events_->nowMs();
    if (id == "camera" && now - lastFrameMs_ < 66) {  // ~15 fps is plenty for the HMI
        return;
    }
    QImage image = toQImage(msg);
    if (image.isNull()) {
        return;
    }
    if (rotate) {
        image = image.transformed(QTransform().rotate(-90));
    }
    images_->setImage(id, image);
    if (id == "camera") {
        lastFrameMs_ = now;
        ++cameraFrame_;
        emit cameraFrameChanged();
    }
}

void RosBridge::onMap(const nav_msgs::msg::OccupancyGrid &msg)
{
    const int w = static_cast<int>(msg.info.width), h = static_cast<int>(msg.info.height);
    if (w <= 0 || h <= 0) {
        return;
    }
    QImage image(w, h, QImage::Format_RGB32);
    for (int y = 0; y < h; ++y) {
        auto *line = reinterpret_cast<QRgb *>(image.scanLine(h - 1 - y));
        for (int x = 0; x < w; ++x) {
            const int v = msg.data[static_cast<size_t>(y * w + x)];
            line[x] = v < 0 ? qRgb(0x0B, 0x0E, 0x13) : v > 50 ? qRgb(0x3A, 0x46, 0x58) : qRgb(0x14, 0x1A, 0x24);
        }
    }
    images_->setImage("map", image);
    mapSize_ = image.size();
    mapResolution_ = msg.info.resolution;
    mapOriginX_ = msg.info.origin.position.x;
    mapOriginY_ = msg.info.origin.position.y;
    ++mapFrame_;
    emit mapChanged();
}

QPointF RosBridge::worldToPixel(double x, double y) const
{
    if (mapResolution_ <= 0) {
        return {-1, -1};
    }
    return {(x - mapOriginX_) / mapResolution_, mapSize_.height() - 1 - (y - mapOriginY_) / mapResolution_};
}

void RosBridge::onPath(const nav_msgs::msg::Path &msg)
{
    pathPixels_.clear();
    const size_t n = msg.poses.size();
    const size_t stride = std::max<size_t>(1, n / 200);
    for (size_t i = 0; i < n; i += stride) {
        pathPixels_.append(worldToPixel(msg.poses[i].pose.position.x, msg.poses[i].pose.position.y));
    }
    if (n > 0) {
        pathPixels_.append(worldToPixel(msg.poses[n - 1].pose.position.x, msg.poses[n - 1].pose.position.y));
    }
    emit pathChanged();
}

void RosBridge::updatePose()
{
    try {
        const auto t = tfBuffer_->lookupTransform("map", kRobotFrame, tf2::TimePointZero);
        const auto &q = t.transform.rotation;
        robotYaw_ = std::atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
        robotPixel_ = worldToPixel(t.transform.translation.x, t.transform.translation.y);
        robotPose_ = QString("x %1 · y %2").arg(t.transform.translation.x, 0, 'f', 1).arg(t.transform.translation.y, 0, 'f', 1);
        emit poseChanged();
    } catch (const tf2::TransformException &) {
        // No transform yet: keep the last pose.
    }
}

// ─── Cameras ──────────────────────────────────────────────────────────────────

void RosBridge::setCameraIndex(int index)
{
    if (index < 0 || index >= 3 || index == cameraIndex_) {
        return;
    }
    cameraIndex_ = index;
    subscribeCamera();
    emit cameraChanged();
}

QString RosBridge::cameraTopic() const
{
    return kCameras[cameraIndex_].topic;
}

void RosBridge::subscribeCamera()
{
    cameraSub_.reset();
    images_->remove("camera");
    rclcpp::QoS qos(rclcpp::KeepLast(2));
    qos.best_effort();
    const Camera &cam = kCameras[cameraIndex_];
    const bool rotate = cam.rotate;
    cameraSub_ = node_->create_subscription<sensor_msgs::msg::Image>(
        cam.topic, qos, [this, rotate](const sensor_msgs::msg::Image &msg) { onImage(msg, "camera", rotate); });
    ++cameraFrame_;
    emit cameraFrameChanged();
}

// ─── Health ───────────────────────────────────────────────────────────────────

QVariantList RosBridge::resources() const
{
    QVariantList list;
    for (const Resource &r : resources_) {
        list.append(QVariantMap{{"name", r.name}, {"value", r.value}, {"history", r.history}});
    }
    return list;
}

QVariantList RosBridge::agents() const
{
    const qint64 now = events_->nowMs();
    const bool utilizationFresh = utilizationMs_ >= 0 && now - utilizationMs_ < 15000;
    const AgentState orchestrator = agentStates_.value("Orchestrator");
    const bool orchestratorAlive = orchestrator.heartbeatMs >= 0 && now - orchestrator.heartbeatMs < kHeartbeatStaleMs;
    QVariantList list;
    for (const auto &a : kAgents) {
        const AgentState s = agentStates_.value(a.name);
        bool alive = s.heartbeatMs >= 0 && now - s.heartbeatMs < kHeartbeatStaleMs;
        bool known = s.heartbeatMs >= 0;
        if (QString(a.group) == "executor") {
            alive = orchestratorAlive;  // executors run inside the orchestrator process
            known = orchestrator.heartbeatMs >= 0;
        }
        if (!known && QString(a.name) == "Nav2" && utilizationFresh) {
            alive = nav2Ok_;
            known = true;
        }
        if (!known && QString(a.name) == "MoveIt2" && utilizationFresh) {
            alive = moveit2Ok_;
            known = true;
        }
        const bool active = s.activeMs >= 0 && now - s.activeMs < kActiveWindowMs;
        QString state = active ? "working" : alive ? "idle" : known ? "offline" : "unknown";
        if (active && !alive && known) state = "working";
        list.append(QVariantMap{{"name", a.name}, {"group", a.group}, {"color", a.color}, {"state", state},
                                {"doing", s.doing.isEmpty() ? QString(alive ? "Waiting for work" : "No heartbeat") : s.doing},
                                {"heartbeatAge", s.heartbeatMs >= 0 ? (now - s.heartbeatMs) / 1000.0 : -1.0}});
    }
    return list;
}

void RosBridge::pollEndpoints()
{
    for (int i = 0; i < endpoints_.size(); ++i) {
        const QVariantMap ep = endpoints_[i].toMap();
        const QString path = ep["backend"].toString() == "NPU" ? "/v1/models" : "/health";
        QString host = ep["host"].toString();
        if (host == "localhost") host = "127.0.0.1";
        QNetworkRequest request(QUrl(QString("http://%1:%2%3").arg(host).arg(ep["port"].toInt()).arg(path)));
        request.setTransferTimeout(3000);
        auto *clock = new QElapsedTimer();
        clock->start();
        QNetworkReply *reply = network_.get(request);
        connect(reply, &QNetworkReply::finished, this, [this, reply, i, clock]() {
            const bool ok = reply->error() == QNetworkReply::NoError;
            const qint64 ms = clock->elapsed();
            delete clock;
            reply->deleteLater();
            if (i >= endpoints_.size()) return;
            QVariantMap ep = endpoints_[i].toMap();
            ep["ok"] = ok;
            ep["checked"] = true;
            ep["latencyMs"] = ok ? ms : -1;
            endpoints_[i] = ep;
            emit endpointsChanged();
        });
    }
}

// ─── Commands ─────────────────────────────────────────────────────────────────

void RosBridge::sendTask(const QString &prompt)
{
    const QString text = prompt.trimmed();
    if (text.isEmpty()) {
        return;
    }
    std_msgs::msg::String msg;
    msg.data = text.toStdString();
    taskPub_->publish(msg);
    emit notify("Task sent: " + firstLine(text, 70), false);
}

void RosBridge::loadScene(const QString &name)
{
    if (!sceneBusy_.isEmpty()) {
        emit notify("Still loading " + sceneBusy_ + ", wait for it to finish", true);
        return;
    }
    auto client = sceneClients_.value(name);
    if (!client || !client->service_is_ready()) {
        emit notify("Scene agent is not available (/rai/scene/" + name + ")", true);
        return;
    }
    sceneBusy_ = name;
    emit sceneChanged();
    auto request = std::make_shared<std_srvs::srv::Trigger::Request>();
    client->async_send_request(request, [this, name](rclcpp::Client<std_srvs::srv::Trigger>::SharedFuture future) {
        const auto response = future.get();
        sceneBusy_.clear();
        if (response->success) {
            loadedScene_ = name == "cleanup" ? QString("empty") : name;
            emit notify(name == "cleanup" ? QString("Scene cleared") : "Scene loaded: " + name, false);
        } else {
            emit notify("Scene " + name + " failed: " + QString::fromStdString(response->message), true);
        }
        emit sceneChanged();
    });
}

void RosBridge::emergencyStop()
{
    estopPub_->publish(std_msgs::msg::Empty());
    drive(0, 0);
    estopped_ = true;
    emit estopChanged();
    emit notify("Emergency stop sent", true);
}

void RosBridge::releaseStop()
{
    releasePub_->publish(std_msgs::msg::Empty());
    estopped_ = false;
    emit estopChanged();
    emit notify("Emergency stop released", false);
}

void RosBridge::drive(double linear, double angular)
{
    geometry_msgs::msg::Twist msg;
    msg.linear.x = linear;
    msg.angular.z = angular;
    cmdVelPub_->publish(msg);
}

void RosBridge::sendGoal(double mapPx, double mapPy)
{
    if (mapResolution_ <= 0) {
        return;
    }
    geometry_msgs::msg::PoseStamped goal;
    goal.header.frame_id = "map";
    goal.header.stamp = node_->now();
    goal.pose.position.x = mapPx * mapResolution_ + mapOriginX_;
    goal.pose.position.y = (mapSize_.height() - 1 - mapPy) * mapResolution_ + mapOriginY_;
    goal.pose.orientation.w = 1.0;
    goalPub_->publish(goal);
    emit notify(QString("Navigation goal sent: x %1 · y %2").arg(goal.pose.position.x, 0, 'f', 1).arg(goal.pose.position.y, 0, 'f', 1), false);
}
