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
#include "Theme.h"
#include "UiKit.h"
#include "ParseRaiData.h"

#include <tf2/exceptions.h>
#include <chrono>
#include <cmath>
#include <functional>
#include <optional>
#include <unordered_map>

#include <QCheckBox>
#include <QFrame>
#include <QGuiApplication>
#include <QScreen>
#include <QGraphicsScene>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QIcon>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QListWidgetItem>
#include <QMessageBox>
#include <QPushButton>
#include <QScrollArea>
#include <QStyle>
#include <QTabWidget>
#include <QTransform>
#include <QVariant>
#include <QVBoxLayout>
#include <rclcpp/qos.hpp>

using ui::Card;
using ui::KeyValue;
using ui::StatBar;
using ui::StatTile;
using ui::StatusPill;
using ui::captionLabel;
using ui::sectionLabel;

// ----------------------------------------------------------------------------
//  small file-local helpers
// ----------------------------------------------------------------------------
namespace {

const std::unordered_map<std::string, int> EncodingMap = {
    {"mono8", QImage::Format_Grayscale8},
    {"rgb8", QImage::Format_RGB888},
    {"rgba8", QImage::Format_RGBA8888},
    {"bgra8", QImage::Format_RGBA8888}, // Will need to swap channels
};

QString HRIMessageToString(const ParseRaiData::HRIMessage& msg)
{
    QStringList paramList;
    for (auto it = msg.parameters_.cbegin(); it != msg.parameters_.cend(); ++it) {
        paramList << QString("%1: %2").arg(it.key(), it.value());
    }
    QString paramsStr = paramList.isEmpty() ? "none" : paramList.join(", ");
    return QString("Calling Tool %1 with params %2").arg(msg.tool_name_, paramsStr);
}

void CallService(QWidget* parent, rclcpp::Node::SharedPtr& node,
                 rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr& client)
{
    if (!client->wait_for_service(std::chrono::seconds(1))) {
        QMessageBox::warning(parent, "Service Call Failed", "Service not available.");
        return;
    }
    auto request = std::make_shared<std_srvs::srv::Trigger::Request>();
    auto result_future = client->async_send_request(request);
    auto status = rclcpp::spin_until_future_complete(node, result_future, std::chrono::seconds(60));
    if (status != rclcpp::FutureReturnCode::SUCCESS) {
        QMessageBox::warning(parent, "Service Call Timeout", "Service did not respond within 60 seconds.");
        return;
    }
    auto response = result_future.get();
    if (!response->success) {
        QMessageBox::warning(parent, "Service Call Failed", QString::fromStdString(response->message));
    }
}

QStringList parsePythonList(QString list)
{
    QStringList done;
    QString listStr = list.trimmed();
    if (listStr.startsWith('[') && listStr.endsWith(']')) {
        listStr = listStr.mid(1, listStr.length() - 2);
    }
    if (!listStr.isEmpty()) {
        const QStringList rawItems = listStr.split('|');
        for (const QString& item : rawItems) {
            QString cleanItem = item.trimmed();
            if (cleanItem.startsWith('"') && cleanItem.endsWith('"')) {
                cleanItem = cleanItem.mid(1, cleanItem.length() - 2);
            } else if (cleanItem.startsWith('\'') && cleanItem.endsWith('\'')) {
                cleanItem = cleanItem.mid(1, cleanItem.length() - 2);
            }
            if (!cleanItem.isEmpty()) done.append(cleanItem);
        }
    }
    return done;
}

// apply a QSS "variant" property (string form, so the const-char* overload of
// setProperty is avoided).
void setVariant(QWidget* w, const QString& variant) { w->setProperty("variant", variant); }

// small inline tag / badge label
QLabel* badge(const QString& text, const QString& bg, const QString& fg)
{
    auto* l = new QLabel(text.toUpper());
    QFont f = l->font();
    f.setPointSizeF(std::max(7.0, f.pointSizeF() - 2.5));
    f.setBold(true);
    l->setFont(f);
    l->setStyleSheet(QString("background:%1; color:%2; border-radius:7px; padding:2px 8px;").arg(bg, fg));
    l->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Maximum);
    return l;
}

QLabel* boldLabel(const QString& text, double sizeDelta = 1.0)
{
    auto* l = new QLabel(text);
    QFont f = l->font();
    f.setPointSizeF(f.pointSizeF() + sizeDelta);
    f.setBold(true);
    l->setFont(f);
    l->setStyleSheet(QString("color:%1; background:transparent;").arg(Theme::Ink));
    return l;
}

QLabel* mono(const QString& text, bool onDark = false, bool rightAlign = false)
{
    auto* l = new QLabel(text);
    l->setStyleSheet(QString("font-family:'DejaVu Sans Mono','Consolas',monospace; color:%1; background:transparent;")
                         .arg(onDark ? Theme::NavyInk : Theme::Ink2));
    if (rightAlign) l->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    return l;
}

// subsystem row: "Name ............ ● state". Returns row widget, outputs pill.
QWidget* subsystemRow(const QString& name, StatusPill** outPill)
{
    auto* w = new QWidget();
    auto* h = new QHBoxLayout(w);
    h->setContentsMargins(0, 4, 0, 4);
    auto* n = new QLabel(name);
    n->setStyleSheet(QString("color:%1; background:transparent; font-weight:600;").arg(Theme::Ink));
    auto* pill = new StatusPill();
    pill->setMinimumWidth(120);
    pill->setState(StatusPill::Idle, "—");
    h->addWidget(n);
    h->addStretch();
    h->addWidget(pill);
    *outPill = pill;
    return w;
}

QFrame* hLine()
{
    auto* line = new QFrame();
    line->setFixedHeight(1);
    line->setStyleSheet(QString("background:%1; border:none;").arg(Theme::Border));
    return line;
}

} // namespace

// ----------------------------------------------------------------------------
//  construction
// ----------------------------------------------------------------------------
HMIWindow::HMIWindow(QWidget* parent) : QMainWindow(parent)
{
    setWindowTitle("Robotnik Kairos+ HMI");

    auto* central = new QWidget();
    central->setObjectName("centralRoot");
    auto* root = new QVBoxLayout(central);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    root->addWidget(buildHeader());

    auto* tabs = new QTabWidget();
    tabs->addTab(buildControlTab(), "Control");
    tabs->addTab(buildStatusTab(), "Status");
    tabs->addTab(buildMissionTab(), "Mission");

    auto* tabWrap = new QWidget();
    auto* tw = new QVBoxLayout(tabWrap);
    tw->setContentsMargins(18, 10, 18, 14);
    tw->addWidget(tabs);
    root->addWidget(tabWrap, 1);

    setCentralWidget(central);
    setStyleSheet(Theme::styleSheet());

    tabs->setCurrentIndex(qEnvironmentVariableIntValue("HMI_DEFAULT_TAB"));

    initRos();

    // periodic ROS spin
    ros_timer_ = new QTimer(this);
    connect(ros_timer_, &QTimer::timeout, this, &HMIWindow::spinROS);
    ros_timer_->start(10);

    if (auto* scr = QGuiApplication::primaryScreen()) setGeometry(scr->geometry());
    showFullScreen();
}

HMIWindow::~HMIWindow()
{
    if (ros_timer_) ros_timer_->stop();
    rclcpp::shutdown();
}

// ----------------------------------------------------------------------------
//  header
// ----------------------------------------------------------------------------
QWidget* HMIWindow::buildHeader()
{
    auto* h = new QFrame();
    h->setObjectName("appHeader");
    h->setFixedHeight(66);
    auto* lay = new QHBoxLayout(h);
    lay->setContentsMargins(24, 0, 18, 0);
    lay->setSpacing(14);

    auto* titles = new QVBoxLayout();
    titles->setSpacing(0);
    auto* title = new QLabel("Robotnik Kairos+ · Agentic HMI");
    title->setObjectName("appTitle");
    auto* sub = new QLabel("Embodied agentic AI — warehouse mobile manipulator");
    sub->setObjectName("appSubtitle");
    titles->addWidget(title);
    titles->addWidget(sub);
    lay->addLayout(titles);
    lay->addStretch();

    agentPill_ = new StatusPill(nullptr, /*onDark=*/true);
    agentPill_->setState(StatusPill::Bad, "agent offline");
    agentPill_->setMinimumWidth(130);
    lay->addWidget(agentPill_);

    auto* stop = new QPushButton("■  EMERGENCY STOP");
    stop->setObjectName("StopButton");
    stop->setCursor(Qt::PointingHandCursor);
    connect(stop, &QPushButton::pressed, [this]() { stop_pub_->publish(std_msgs::msg::String()); });
    lay->addWidget(stop);

    return h;
}

// ----------------------------------------------------------------------------
//  Control tab
// ----------------------------------------------------------------------------
QWidget* HMIWindow::buildControlTab()
{
    auto* scroll = new QScrollArea();
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    auto* page = new QWidget();
    auto* col = new QVBoxLayout(page);
    col->setContentsMargins(2, 2, 2, 2);
    col->setSpacing(14);

    // ---- intro / how it works ----
    {
        auto* info = new Card(QString(), Card::Info);
        info->body()->setSpacing(6);
        info->body()->addWidget(boldLabel("How this works", 1.5));
        auto* txt = captionLabel(
            "Pick a warehouse scenario to set the scene, then hand the robot a job. "
            "The agent plans and executes it autonomously — watch progress live on the "
            "Mission tab and node health on the Status tab. Use Emergency Stop at any time.");
        info->body()->addWidget(txt);
        col->addWidget(info);
    }

    // ---- setup the warehouse ----
    {
        auto* card = new Card("Setup the warehouse");
        card->body()->addWidget(captionLabel(
            "Spawn the props and anomalies for a run. This resets and re-populates the simulated warehouse."));

        auto* rowW = new QWidget();
        auto* row = new QHBoxLayout(rowW);
        row->setContentsMargins(0, 0, 0, 0);
        row->setSpacing(12);

        auto scenarioCard = [&](const QString& title, const QString& desc, bool recommended,
                                rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr* client) {
            auto* c = new Card(QString(), Card::Inset);
            c->body()->setSpacing(8);
            c->setMinimumHeight(168);

            auto* head = new QHBoxLayout();
            head->setContentsMargins(0, 0, 0, 0);
            head->addWidget(boldLabel(title, 1.5));
            head->addStretch();
            if (recommended) head->addWidget(badge("recommended", "#e2eefe", Theme::Blue));
            c->body()->addLayout(head);

            c->body()->addWidget(captionLabel(desc), 1);
            auto* b = new QPushButton("Spawn scenario");
            setVariant(b, recommended ? "accent" : "ghost");
            b->setCursor(Qt::PointingHandCursor);
            connect(b, &QPushButton::clicked, [this, client]() { CallService(this, node_, *client); });
            c->body()->addWidget(b);
            return c;
        };

        row->addWidget(scenarioCard("Standard", "A balanced warehouse with package returns to sort and routine housekeeping.", true, &standard_srv_), 1);
        row->addWidget(scenarioCard("Housekeeping", "Items left out of place across racks for the robot to tidy up.", false, &housekeep_srv_), 1);
        row->addWidget(scenarioCard("Anomalies", "Spills, blocked paths and hazards seeded for the safety agent to find.", false, &anomalies_srv_), 1);
        row->addWidget(scenarioCard("Cleanup", "Clear the scene back to an empty, well-ordered warehouse.", false, &cleanup_srv_), 1);
        card->body()->addWidget(rowW);

        auto* footer = new QHBoxLayout();
        footer->addStretch();
        restartButton_ = new QPushButton("Restart orchestrator");
        setVariant(restartButton_, "link");
        restartButton_->setCursor(Qt::PointingHandCursor);
        connect(restartButton_, &QPushButton::clicked, [this]() { CallService(this, node_, restart_srv_); });
        footer->addWidget(restartButton_);
        card->body()->addLayout(footer);

        col->addWidget(card);
    }

    // ---- tell the robot what to do ----
    {
        auto* card = new Card("Tell the robot what to do");
        card->body()->addWidget(captionLabel(
            "Dispatch a job to the agent. It will decide the steps and carry them out on its own."));

        // quick action cards
        auto* quickW = new QWidget();
        auto* quick = new QHBoxLayout(quickW);
        quick->setContentsMargins(0, 0, 0, 0);
        quick->setSpacing(12);

        auto actionCard = [&](const QString& title, const QString& desc, const QString& btnText,
                              std::function<void()> onClick) {
            auto* c = new Card(QString(), Card::Inset);
            c->body()->setSpacing(8);
            c->setMinimumHeight(176);
            c->body()->addWidget(boldLabel(title, 1.5));
            c->body()->addWidget(captionLabel(desc), 1);
            auto* b = new QPushButton(btnText);
            setVariant(b, "primary");
            b->setCursor(Qt::PointingHandCursor);
            connect(b, &QPushButton::clicked, onClick);
            c->body()->addWidget(b);
            return c;
        };

        quick->addWidget(actionCard(
            "Sort package returns",
            "Drive to the returns area and sort returned packages onto the correct racks.",
            "Start sorting",
            [this]() { publishPrompt(HardcodedConfig::taskAPrompt); }), 1);

        // housekeeping cycles through racks; the hint shows the next target
        auto* houseCard = new Card(QString(), Card::Inset);
        houseCard->body()->setSpacing(8);
        houseCard->setMinimumHeight(176);
        houseCard->body()->addWidget(boldLabel("Housekeeping", 1.5));
        houseCard->body()->addWidget(captionLabel("Tidy a single rack — the robot returns stray items to their slots."), 1);
        housekeepingHint_ = captionLabel(QString("Next rack: %1")
                                             .arg(QString::fromStdString(HardcodedConfig::racks[current_rack_index_])));
        houseCard->body()->addWidget(housekeepingHint_);
        {
            auto* b = new QPushButton("Tidy next rack");
            setVariant(b, "primary");
            b->setCursor(Qt::PointingHandCursor);
            connect(b, &QPushButton::clicked, [this]() {
                publishPrompt(HardcodedConfig::taskBPrompt + HardcodedConfig::racks[current_rack_index_]);
                current_rack_index_ = (current_rack_index_ + 1) % HardcodedConfig::racks.size();
                if (housekeepingHint_)
                    housekeepingHint_->setText(QString("Next rack: %1")
                                                   .arg(QString::fromStdString(HardcodedConfig::racks[current_rack_index_])));
            });
            houseCard->body()->addWidget(b);
        }
        quick->addWidget(houseCard, 1);

        quick->addWidget(actionCard(
            "Inspect for hazards",
            "Patrol the warehouse with the VLM and report spills, blockages and anomalies on the Mission tab.",
            "Begin inspection",
            [this]() { publishPrompt(HardcodedConfig::taskInspectPrompt); }), 1);

        card->body()->addWidget(quickW);
        card->body()->addWidget(hLine());

        // shipment + free-form + manual control row
        auto* botW = new QWidget();
        auto* bot = new QHBoxLayout(botW);
        bot->setContentsMargins(0, 0, 0, 0);
        bot->setSpacing(12);

        // prepare shipment
        {
            auto* c = new Card(QString(), Card::Inset);
            c->body()->setSpacing(8);
            c->body()->addWidget(boldLabel("Prepare a shipment", 1.5));
            c->body()->addWidget(captionLabel("Select items to pick, pack and stage for shipping."));
            auto* grid = new QGridLayout();
            grid->setHorizontalSpacing(18);
            grid->setVerticalSpacing(4);
            hammersCheck_ = new QCheckBox("hammers");
            cpuCheck_ = new QCheckBox("CPU");
            gpuCheck_ = new QCheckBox("GPU");
            pipesCheck_ = new QCheckBox("pipes");
            nailsCheck_ = new QCheckBox("nails");
            motherboardCheck_ = new QCheckBox("motherboard");
            grid->addWidget(hammersCheck_, 0, 0);
            grid->addWidget(cpuCheck_, 0, 1);
            grid->addWidget(gpuCheck_, 1, 0);
            grid->addWidget(pipesCheck_, 1, 1);
            grid->addWidget(nailsCheck_, 2, 0);
            grid->addWidget(motherboardCheck_, 2, 1);
            c->body()->addLayout(grid);
            c->body()->addStretch();
            auto* b = new QPushButton("Prepare shipment");
            setVariant(b, "primary");
            b->setCursor(Qt::PointingHandCursor);
            connect(b, &QPushButton::clicked, [this]() {
                std::string data = HardcodedConfig::taskCPrompt;
                if (cpuCheck_->isChecked()) data += "one CPU, ";
                if (gpuCheck_->isChecked()) data += "one GPU, ";
                if (pipesCheck_->isChecked()) data += "pipes, ";
                if (hammersCheck_->isChecked()) data += "hammers, ";
                if (nailsCheck_->isChecked()) data += "nails, ";
                if (motherboardCheck_->isChecked()) data += "motherboard, ";
                publishPrompt(data);
            });
            c->body()->addWidget(b);
            bot->addWidget(c, 2);
        }

        // free-form task
        {
            auto* c = new Card(QString(), Card::Inset);
            c->body()->setSpacing(8);
            c->body()->addWidget(boldLabel("Free-form task", 1.5));
            c->body()->addWidget(captionLabel("Type any instruction in plain English. The agent parses and plans it."));
            freeFormEdit_ = new QLineEdit();
            freeFormEdit_->setPlaceholderText("e.g. Bring two hammers to the packing table");
            c->body()->addWidget(freeFormEdit_);
            c->body()->addStretch();
            auto* b = new QPushButton("Run task");
            setVariant(b, "primary");
            b->setCursor(Qt::PointingHandCursor);
            auto run = [this]() {
                const QString t = freeFormEdit_->text().trimmed();
                if (!t.isEmpty()) {
                    publishPrompt(t.toStdString());
                    freeFormEdit_->clear();
                }
            };
            connect(b, &QPushButton::clicked, run);
            connect(freeFormEdit_, &QLineEdit::returnPressed, run);
            c->body()->addWidget(b);
            bot->addWidget(c, 2);
        }

        // manual control d-pad
        {
            auto* c = new Card(QString(), Card::Inset);
            c->body()->setSpacing(8);
            c->body()->addWidget(boldLabel("Manual control", 1.5));
            c->body()->addWidget(captionLabel("Nudge the base directly."));
            auto* pad = new QGridLayout();
            pad->setSpacing(6);
            auto mkBtn = [&](const QString& icon, int dx, int dy, double lin, double ang) {
                auto* b = new QPushButton();
                setVariant(b, "teleop");
                b->setIcon(QIcon(icon));
                b->setIconSize(QSize(26, 26));
                connect(b, &QPushButton::pressed, [this, lin, ang]() { publishCmdVel(lin, ang); });
                connect(b, &QPushButton::released, [this]() { publishCmdVel(0.0, 0.0); });
                pad->addWidget(b, dy, dx);
                return b;
            };
            mkBtn(":/icons/Up.svg", 1, 0, 0.5, 0.0);
            mkBtn(":/icons/Left.svg", 0, 1, 0.0, 0.5);
            mkBtn(":/icons/Right.svg", 2, 1, 0.0, -0.5);
            mkBtn(":/icons/Down.svg", 1, 2, -0.5, 0.0);
            auto* padWrap = new QHBoxLayout();
            padWrap->addStretch();
            padWrap->addLayout(pad);
            padWrap->addStretch();
            c->body()->addStretch();
            c->body()->addLayout(padWrap);
            c->body()->addStretch();
            bot->addWidget(c, 1);
        }

        card->body()->addWidget(botW);
        col->addWidget(card);
    }

    col->addStretch();
    scroll->setWidget(page);
    return scroll;
}

// ----------------------------------------------------------------------------
//  Status tab
// ----------------------------------------------------------------------------
QWidget* HMIWindow::buildStatusTab()
{
    auto* scroll = new QScrollArea();
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    auto* page = new QWidget();
    auto* grid = new QGridLayout(page);
    grid->setContentsMargins(2, 2, 2, 2);
    grid->setHorizontalSpacing(14);
    grid->setVerticalSpacing(14);
    grid->setColumnStretch(0, 1);
    grid->setColumnStretch(1, 1);

    // ---- system resources ----
    {
        auto* card = new Card("System resources");
        auto* row = new QHBoxLayout();
        row->setSpacing(22);
        cpuBar_ = new StatBar("CPU");
        ramBar_ = new StatBar("RAM");
        gpuBar_ = new StatBar("GPU");
        diskBar_ = new StatBar("DISK");
        row->addWidget(cpuBar_);
        row->addWidget(ramBar_);
        row->addWidget(gpuBar_);
        row->addWidget(diskBar_);
        card->body()->addLayout(row);
        grid->addWidget(card, 0, 0, 1, 2);
    }

    // ---- VRAM (navy) ----
    {
        auto* card = new Card(QString(), Card::Navy);
        auto* head = new QHBoxLayout();
        head->addWidget(sectionLabel("VRAM · UMA shared · gfx1151", true));
        head->addStretch();
        head->addWidget(captionLabel("rocm-smi · 1 Hz", true));
        card->body()->addLayout(head);
        vramBar_ = new StatBar("Allocated", nullptr, /*onDark=*/true);
        card->body()->addWidget(vramBar_);
        grid->addWidget(card, 1, 0, 1, 2);
    }

    // ---- AI models ----
    {
        auto* card = new Card("AI models");
        auto* t = new QGridLayout();
        t->setHorizontalSpacing(18);
        t->setVerticalSpacing(2);
        t->setColumnStretch(0, 3);
        t->setColumnStretch(1, 1);
        t->setColumnStretch(2, 1);
        t->setColumnStretch(3, 1);
        t->setColumnStretch(4, 1);

        auto hdr = [&](const QString& s, int col, bool right = false) {
            auto* l = sectionLabel(s);
            if (right) l->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
            t->addWidget(l, 0, col);
        };
        hdr("Model", 0);
        hdr("Port", 1);
        hdr("VRAM", 2, true);
        hdr("Decode", 3, true);
        hdr("Slots", 4, true);

        int r = 1;
        for (const auto& m : HardcodedConfig::AiModels) {
            auto* nameW = new QWidget();
            auto* nh = new QHBoxLayout(nameW);
            nh->setContentsMargins(0, 6, 0, 6);
            nh->setSpacing(8);
            auto* dot = new StatusPill();
            dot->setState(StatusPill::Idle, QString::fromLatin1(m.name));
            dot->setMinimumWidth(150);
            nh->addWidget(dot);
            nh->addWidget(captionLabel(QString::fromLatin1(m.role)));
            nh->addStretch();
            t->addWidget(nameW, r, 0);
            t->addWidget(mono(QString::fromLatin1(m.port)), r, 1);
            t->addWidget(mono(QString::fromLatin1(m.vram), false, true), r, 2);
            t->addWidget(mono("idle", false, true), r, 3);
            t->addWidget(mono("0", false, true), r, 4);
            ++r;
        }
        card->body()->addLayout(t);
        grid->addWidget(card, 2, 0, 1, 2);
    }

    // ---- simulation ----
    {
        auto* card = new Card("Simulation");
        card->body()->addWidget(new KeyValue("FPS", "(not published)"));
        card->body()->addWidget(new KeyValue("Sim clock", "(not published)"));
        card->body()->addWidget(new KeyValue("Entities", "(not polled)"));
        card->body()->addWidget(new KeyValue("Wrist cam", "—"));
        card->body()->addStretch();
        grid->addWidget(card, 3, 0);
    }

    // ---- last LLM call ----
    {
        auto* card = new Card("Last LLM call");
        card->body()->addWidget(new KeyValue("Model", "gpt-oss-20b"));
        card->body()->addWidget(new KeyValue("Latency", "—"));
        card->body()->addWidget(new KeyValue("Tokens in / out", "—"));
        card->body()->addWidget(new KeyValue("Tool", "—"));
        card->body()->addStretch();
        grid->addWidget(card, 3, 1);
    }

    // ---- subsystems ----
    {
        auto* card = new Card("Subsystems");
        card->body()->addWidget(subsystemRow("Nav2", &nav2Pill_));
        card->body()->addWidget(subsystemRow("MoveIt2", &moveit2Pill_));
        card->body()->addWidget(subsystemRow("Orchestrator", &orchestratorPill_));
        card->body()->addWidget(subsystemRow("DDS shm", &ddsPill_));
        card->body()->addWidget(subsystemRow("Watchdog", &watchdogPill_));
        card->body()->addWidget(subsystemRow("/get_entities_states", &entitiesPill_));
        nav2Pill_->setState(StatusPill::Unknown, "—");
        moveit2Pill_->setState(StatusPill::Unknown, "—");
        orchestratorPill_->setState(StatusPill::Bad, "no heartbeat");
        card->body()->addStretch();
        grid->addWidget(card, 4, 0);
    }

    // ---- run stats ----
    {
        auto* card = new Card("Run stats · harness");
        for (const char* k : {"Tag", "Iters total", "  completed", "  timeout", "  stuck",
                              "Sort returns", "Housekeep rack", "Tool calls (CSV)",
                              "Tool errors (CSV)", "lfm2-vl restarts"}) {
            card->body()->addWidget(new KeyValue(QString::fromLatin1(k), "—"));
        }
        card->body()->addStretch();
        grid->addWidget(card, 4, 1);
    }

    // ---- event timeline (live rosout) ----
    {
        auto* card = new Card("Event timeline");
        card->body()->addWidget(captionLabel("Live agent & navigation events (newest at top)."));
        listLog_ = new QListWidget();
        listLog_->setMinimumHeight(200);
        card->body()->addWidget(listLog_);
        grid->addWidget(card, 5, 0, 1, 2);
    }

    // ---- last warning ----
    {
        auto* card = new Card(QString(), Card::Inset);
        auto* h = new QHBoxLayout();
        h->addWidget(sectionLabel("Last warning"));
        lastWarningLabel_ = new QLabel("no warnings yet");
        lastWarningLabel_->setStyleSheet(QString("color:%1; background:transparent;").arg(Theme::Ink2));
        h->addSpacing(12);
        h->addWidget(lastWarningLabel_, 1);
        card->body()->addLayout(h);
        grid->addWidget(card, 6, 0, 1, 2);
    }

    grid->setRowStretch(7, 1);
    scroll->setWidget(page);
    return scroll;
}

// ----------------------------------------------------------------------------
//  Mission tab
// ----------------------------------------------------------------------------
QWidget* HMIWindow::buildMissionTab()
{
    auto* page = new QWidget();
    auto* outer = new QVBoxLayout(page);
    outer->setContentsMargins(2, 2, 2, 2);
    outer->setSpacing(14);

    // ---- top: mission status strip + scene control ----
    {
        auto* topRow = new QHBoxLayout();
        topRow->setSpacing(14);

        auto* status = new Card(QString(), Card::Navy);
        auto* head = new QHBoxLayout();
        head->addWidget(sectionLabel("COGFRAME · v1.2", true));
        head->addStretch();
        head->addWidget(captionLabel("waiting for harness…", true));
        status->body()->addLayout(head);

        auto* tiles = new QHBoxLayout();
        tiles->setSpacing(10);
        auto addTile = [&](const QString& cap, const QString& val, StatTile** out = nullptr) {
            auto* tile = new StatTile(cap, nullptr, /*onDark=*/true);
            tile->setValue(val);
            tiles->addWidget(tile);
            if (out) *out = tile;
        };
        StatTile* drive = nullptr;
        addTile("Drive", "IDLE", &drive);
        addTile("Task", "—", &taskTile_);
        addTile("Iter", "0 / 0");
        addTile("Phase", "—");
        addTile("Elapsed", "—");
        addTile("Drift", "0");
        status->body()->addLayout(tiles);
        topRow->addWidget(status, 3);

        auto* scene = new Card("Scene control");
        scene->body()->addWidget(captionLabel("Reset the warehouse and orchestrator to a clean state."));
        auto* reset = new QPushButton("Reset scene");
        setVariant(reset, "primary");
        reset->setCursor(Qt::PointingHandCursor);
        connect(reset, &QPushButton::clicked, [this]() { CallService(this, node_, restart_srv_); });
        scene->body()->addStretch();
        scene->body()->addWidget(reset);
        topRow->addWidget(scene, 1);

        outer->addLayout(topRow);
    }

    // ---- main: observer/agent-task | vlm output ----
    auto* mainRow = new QHBoxLayout();
    mainRow->setSpacing(14);

    // left column
    {
        auto* leftCol = new QVBoxLayout();
        leftCol->setSpacing(14);

        // mission observer
        auto* obs = new Card("Mission observer");
        auto* viewsRow = new QHBoxLayout();
        viewsRow->setSpacing(12);

        auto makeView = [&](const QString& title, QGraphicsView* view, QWidget* headerExtra = nullptr) {
            auto* v = new QVBoxLayout();
            v->setSpacing(6);
            auto* hb = new QHBoxLayout();
            hb->setContentsMargins(0, 0, 0, 0);
            hb->addWidget(sectionLabel(title));
            hb->addStretch();
            if (headerExtra) hb->addWidget(headerExtra);
            v->addLayout(hb);
            view->setMinimumSize(300, 230);
            view->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
            v->addWidget(view, 1);
            return v;
        };

        // camera selector buttons sit in the first view's header
        auto* camSel = new QWidget();
        auto* csl = new QHBoxLayout(camSel);
        csl->setContentsMargins(0, 0, 0, 0);
        csl->setSpacing(4);
        auto* btn1 = new QPushButton("1");
        auto* btn2 = new QPushButton("2");
        for (auto* b : {btn1, btn2}) {
            setVariant(b, "camsel");
            b->setCursor(Qt::PointingHandCursor);
        }
        csl->addWidget(btn1);
        csl->addWidget(btn2);
        camera_buttons_["Camera 1"] = btn1;
        camera_buttons_["Camera 2"] = btn2;
        connect(btn1, &QPushButton::clicked, [this]() { cameraButtonCallback("Camera 1"); });
        connect(btn2, &QPushButton::clicked, [this]() { cameraButtonCallback("Camera 2"); });

        graphicsViewCameras_ = new QGraphicsView();
        topCameraGraphicsView_ = new QGraphicsView();
        graphicsViewMap_ = new ZoomableGraphicsView();

        viewsRow->addLayout(makeView("Base / wrist camera", graphicsViewCameras_, camSel), 1);
        viewsRow->addLayout(makeView("Top view", topCameraGraphicsView_), 1);
        viewsRow->addLayout(makeView("Map", graphicsViewMap_), 1);
        obs->body()->addLayout(viewsRow, 1);
        leftCol->addWidget(obs, 3);

        // agent task
        auto* at = new Card("Agent task");
        at->body()->addWidget(sectionLabel("Current task"));
        currentTask_ = new LogItemWidget(QString(), QPixmap(), QColor(Theme::Amber), TextMode::Wrap, false, this);
        currentTask_->setFixedHeight(72);
        currentTask_->setText("No current task.");
        at->body()->addWidget(currentTask_);

        at->body()->addWidget(sectionLabel("Current action"));
        currentAction_ = new LogItemWidget(QString(), QPixmap(), QColor(Theme::Green), TextMode::Detail, false, this);
        currentAction_->setFixedHeight(72);
        currentAction_->setText("No current action.");
        at->body()->addWidget(currentAction_);

        at->body()->addWidget(sectionLabel("Plan & history"));
        queueView_ = new LogView(this);
        listTaskLayout_ = new QVBoxLayout();
        listTaskLayout_->addWidget(queueView_);
        at->body()->addLayout(listTaskLayout_, 1);
        leftCol->addWidget(at, 2);

        mainRow->addLayout(leftCol, 1);
    }

    // right column
    {
        auto* rightCol = new QVBoxLayout();
        rightCol->setSpacing(14);

        auto* vlm = new Card("VLM output");
        auto* statsRow = new QHBoxLayout();
        statsRow->setSpacing(10);
        for (const char* cap : {"Drives", "Success", "Avg drift", "Avg dur"}) {
            auto* tile = new StatTile(QString::fromLatin1(cap));
            tile->setValue(QString::fromLatin1(cap) == QString("Drives") ? "0" : "—");
            statsRow->addWidget(tile);
        }
        vlm->body()->addLayout(statsRow);
        vlm->body()->addWidget(captionLabel(
            "Live scene descriptions and hazard analysis from the vision-language model."));
        logView_ = new LogView(this);
        vlmLayout_ = new QVBoxLayout();
        vlmLayout_->addWidget(logView_);
        vlm->body()->addLayout(vlmLayout_, 1);
        rightCol->addWidget(vlm, 3);

        auto* tools = new Card("Tool calls");
        tools->body()->addWidget(captionLabel("Most recent tools invoked by the agent."));
        tools->body()->addWidget(new KeyValue("Waiting for activity…", " "));
        tools->body()->addStretch();
        rightCol->addWidget(tools, 1);

        mainRow->addLayout(rightCol, 1);
    }

    outer->addLayout(mainRow, 1);
    return page;
}

// ----------------------------------------------------------------------------
//  ROS wiring
// ----------------------------------------------------------------------------
void HMIWindow::initRos()
{
    rclcpp::init(0, nullptr);
    node_ = rclcpp::Node::make_shared("hmi_window_node");

    cmd_vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>(HardcodedConfig::CmdVelTopic, 10);
    goal_pub_ = node_->create_publisher<geometry_msgs::msg::PoseStamped>(HardcodedConfig::GoalTopic, 10);
    stop_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::EmergencyStopTopic, 10);
    user_prompt_pub_ = node_->create_publisher<std_msgs::msg::String>(HardcodedConfig::UserPromptTopic, 10);

    map_sub_ = node_->create_subscription<nav_msgs::msg::OccupancyGrid>(
        HardcodedConfig::MapTopic, 10,
        [this](const nav_msgs::msg::OccupancyGrid::SharedPtr msg) { mapCallback(msg); });

    path_sub_ = node_->create_subscription<nav_msgs::msg::Path>(
        HardcodedConfig::PathTopic, 10,
        [this](const nav_msgs::msg::Path::SharedPtr msg) { graphicsViewMap_->drawPlan(msg); });

    utilization_sub_ = node_->create_subscription<demo_msgs::msg::Utilization>(
        "/utilization", 10,
        [this](const demo_msgs::msg::Utilization::SharedPtr msg) {
            std::unordered_map<std::string, float> values;
            const size_t n = std::min(msg->component_names.size(), msg->component_values.size());
            for (size_t i = 0; i < n; ++i) values[msg->component_names[i]] = msg->component_values[i];
            auto get = [&values](const char* key) -> std::optional<float> {
                auto it = values.find(key);
                if (it == values.end()) return std::nullopt;
                return it->second;
            };
            if (auto v = get("cpu"); v) cpuBar_->setValue(*v);
            if (auto v = get("ram"); v) ramBar_->setValue(*v);
            if (auto v = get("gpu"); v) gpuBar_->setValue(*v);
            nav2Pill_->setState(msg->nav2_state ? StatusPill::Ok : StatusPill::Bad,
                                msg->nav2_state ? "online" : "down");
            moveit2Pill_->setState(msg->moveit2_state ? StatusPill::Ok : StatusPill::Bad,
                                   msg->moveit2_state ? "online" : "down");
        });

    log_sub_ = node_->create_subscription<rcl_interfaces::msg::Log>(
        "/rosout", 10,
        [this](const rcl_interfaces::msg::Log::SharedPtr msg) { logCallback(msg); });

    tf_buffer_ = std::make_unique<tf2_ros::Buffer>(node_->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    connect(graphicsViewMap_, &ZoomableGraphicsView::goalSet, [this](float x, float y) {
        RCLCPP_INFO(node_->get_logger(), "Goal set at (%.2f, %.2f)", x, y);
        geometry_msgs::msg::PoseStamped goal_msg;
        goal_msg.header.frame_id = "map";
        goal_msg.pose.position.x = x;
        goal_msg.pose.position.y = y;
        goal_msg.pose.orientation.w = 1.0;
        goal_pub_->publish(goal_msg);
    });

    graphicsViewMap_->setDragMode(QGraphicsView::RubberBandDrag);
    graphicsViewMap_->setRenderHint(QPainter::Antialiasing);
    graphicsViewMap_->setTransformationAnchor(QGraphicsView::AnchorUnderMouse);

    vlmLayout_->addWidget(logView_);

    vlm_topic_sub_ = node_->create_subscription<demo_msgs::msg::VlmDescription>(
        HardcodedConfig::VLMTopic, 10,
        [this](const demo_msgs::msg::VlmDescription::SharedPtr msg) {
            QString label = QString::fromStdString(msg->description);
            QImage image;
            if (auto enc = EncodingMap.find(msg->image.encoding); enc != EncodingMap.end()) {
                image = QImage(msg->image.data.data(), static_cast<int>(msg->image.width),
                               static_cast<int>(msg->image.height),
                               static_cast<QImage::Format>(EncodingMap.at(msg->image.encoding)));
            }
            QColor color = HardcodedConfig::Colors.count(msg->source)
                               ? HardcodedConfig::Colors.at(msg->source)
                               : QColor(Theme::Blue);
            auto* item = new LogItemWidget(label, QPixmap::fromImage(image), color, TextMode::Detail, true, this);
            logView_->addItem(item);
        });

    restart_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::Restart);
    housekeep_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::HousekeepService);
    anomalies_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::AnomaliesService);
    standard_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::StandardService);
    cleanup_srv_ = node_->create_client<std_srvs::srv::Trigger>(HardcodedConfig::CleanupService);

    current_action_sub_ = node_->create_subscription<rai_interfaces::msg::HRIMessage>(
        HardcodedConfig::AgentCurrentAction, 10,
        [this](const rai_interfaces::msg::HRIMessage::SharedPtr msg) {
            QString new_id = QString::fromStdString(msg->communication_id);
            if (currentActionCommId_ != new_id) {
                currentActionText_ = QString::fromStdString(msg->text);
                if (auto parsed = ParseRaiData::parseHRIMessage(currentActionText_); parsed.has_value()) {
                    currentActionText_ = HRIMessageToString(parsed.value());
                }
                currentActionCommId_ = new_id;
            } else {
                currentActionText_ += QString::fromStdString(msg->text);
            }
            currentAction_->setText(currentActionText_);
        });

    orchestrator_current_task_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::OrchestratorCurrentTask, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            const QString t = QString::fromStdString(msg->data);
            currentTask_->setText(t.isEmpty() ? "No current task." : t);
            if (taskTile_) taskTile_->setValue(t.isEmpty() ? "—" : t.left(18));
        });

    agent_past_steps_sub_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::AgentPastSteps, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            past_steps_ = parsePythonList(QString::fromStdString(msg->data));
            buildListTask();
        });

    orchestrator_task_queue_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::OrchestratorTaskQueue, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            task_queue_ = parsePythonList(QString::fromStdString(msg->data));
            buildListTask();
        });

    orchestrator_paused_task_ = node_->create_subscription<std_msgs::msg::String>(
        HardcodedConfig::OrchestratorPausedTask, 10,
        [this](const std_msgs::msg::String::SharedPtr msg) {
            paused_tasks_ = parsePythonList(QString::fromStdString(msg->data));
            buildListTask();
        });

    // orchestrator heartbeat drives the header + subsystem pills
    orchestrator_timer_ = new QTimer(this);
    connect(orchestrator_timer_, &QTimer::timeout, [this]() {
        agentPill_->setState(StatusPill::Bad, "agent offline");
        orchestratorPill_->setState(StatusPill::Bad, "no heartbeat");
    });
    orchestrator_sub_ = node_->create_subscription<std_msgs::msg::Header>(
        HardcodedConfig::OrchestratorHeartbeat, 10,
        [this](const std_msgs::msg::Header&) {
            orchestrator_timer_->stop();
            agentPill_->setState(StatusPill::Ok, "agent online");
            orchestratorPill_->setState(StatusPill::Ok, "online");
            orchestrator_timer_->start(static_cast<int>(1000 / HardcodedConfig::OrchestratorHeartbeatFrequency));
        });
}

// ----------------------------------------------------------------------------
//  callbacks
// ----------------------------------------------------------------------------
void HMIWindow::publishPrompt(const std::string& prompt)
{
    std_msgs::msg::String msg;
    msg.data = prompt;
    user_prompt_pub_->publish(msg);
    RCLCPP_INFO(node_->get_logger(), "Published user task: %s", prompt.c_str());
}

void HMIWindow::cameraButtonCallback(const std::string& cameraName)
{
    for (const auto& [name, button] : camera_buttons_) {
        button->setProperty("active", name == cameraName);
        button->style()->unpolish(button);
        button->style()->polish(button);
    }
    auto topic = HardcodedConfig::CameraTopics.at(cameraName);
    RCLCPP_INFO(node_->get_logger(), "Subscribing to camera topic: %s", topic.c_str());
    image_sub_.reset();
    {
        rclcpp::QoS image_qos(rclcpp::KeepLast(5));
        image_qos.best_effort();
        image_qos.durability_volatile();
        image_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(
            topic, image_qos, [this](const sensor_msgs::msg::Image::SharedPtr msg) {
                imageCallback(msg, graphicsViewCameras_);
            });
    }
    if (!top_image_sub_) {
        rclcpp::QoS top_qos(rclcpp::KeepLast(5));
        top_qos.best_effort();
        top_qos.durability_volatile();
        top_image_sub_ = node_->create_subscription<sensor_msgs::msg::Image>(
            "/camera_image_color", top_qos, [this](const sensor_msgs::msg::Image::SharedPtr msg) {
                imageCallback(msg, topCameraGraphicsView_);
            });
    }
}

void HMIWindow::spinROS()
{
    rclcpp::spin_some(node_);
    updateRobotPose();
}

void HMIWindow::buildListTask()
{
    queueView_->clear();
    for (const QString& item : past_steps_) {
        auto* w = new LogItemWidget(QString(), QPixmap(), QColor(HardcodedConfig::Colors.at("PastSteps")),
                                    TextMode::Wrap, false, this);
        w->setText(item);
        queueView_->addItem(w);
    }
    for (const QString& item : task_queue_) {
        auto* w = new LogItemWidget(QString(), QPixmap(), QColor(HardcodedConfig::Colors.at("TaskQueue")),
                                    TextMode::Wrap, false, this);
        w->setText(item);
        queueView_->addItem(w);
    }
}

void HMIWindow::imageCallback(const sensor_msgs::msg::Image::SharedPtr msg, QGraphicsView* view)
{
    Q_ASSERT(view);
    if (auto encoding = EncodingMap.find(msg->encoding); encoding != EncodingMap.end()) {
        QImage image(msg->data.data(), static_cast<int>(msg->width), static_cast<int>(msg->height),
                     QImage::Format_RGBA8888);
        if (view == topCameraGraphicsView_) {
            QTransform rotateLeft;
            rotateLeft.rotate(-90.0);
            image = image.transformed(rotateLeft);
        }
        if (!view->scene()) view->setScene(new QGraphicsScene());
        view->scene()->clear();
        view->scene()->addPixmap(QPixmap::fromImage(image));
        view->fitInView(view->scene()->itemsBoundingRect(), Qt::KeepAspectRatio);
    } else {
        RCLCPP_WARN(node_->get_logger(), "Unsupported image encoding: %s", msg->encoding.c_str());
    }
}

void HMIWindow::mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg)
{
    RCLCPP_INFO(node_->get_logger(), "Received map: %dx%d, resolution: %.3f",
                msg->info.width, msg->info.height, msg->info.resolution);
    graphicsViewMap_->drawMap(msg);
    map_sub_.reset();
}

void HMIWindow::updateRobotPose()
{
    try {
        auto transform = tf_buffer_->lookupTransform("map", HardcodedConfig::RobotBaseFrame, tf2::TimePointZero);
        float x = transform.transform.translation.x;
        float y = transform.transform.translation.y;
        auto& q = transform.transform.rotation;
        float theta = atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
        graphicsViewMap_->drawRobot(x, y, theta);
    } catch (tf2::TransformException& ex) {
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
    if (HardcodedConfig::LogFilter.find(msg->name) == HardcodedConfig::LogFilter.end()) return;
    if (msg->level < HardcodedConfig::MinLogLevel) return;

    const char* level_names[] = {"DEBUG", "INFO", "WARN", "ERROR", "FATAL"};
    const char* level_name = (msg->level >= 10 && msg->level <= 50) ? level_names[(msg->level - 10) / 10] : "UNKNOWN";

    QString color;
    switch (msg->level) {
        case 10: color = "#808080"; break;
        case 20: color = Theme::Ink; break;
        case 30: color = Theme::Amber; break;
        case 40: color = Theme::Red; break;
        case 50: color = "#8B0000"; break;
        default: color = Theme::Ink; break;
    }

    auto msgLine = QString("[%1] %2: %3")
                       .arg(level_name, QString::fromStdString(msg->name), QString::fromStdString(msg->msg));

    if (listLog_) {
        auto* item = new QListWidgetItem(msgLine);
        item->setForeground(QColor(color));
        listLog_->insertItem(0, item);
        if (listLog_->count() > HardcodedConfig::MaxLogEntries) {
            delete listLog_->takeItem(listLog_->count() - 1);
        }
    }

    if (msg->level >= 30 && lastWarningLabel_) {
        lastWarningLabel_->setText(QString::fromStdString(msg->msg));
        lastWarningLabel_->setStyleSheet(QString("color:%1; background:transparent; font-weight:600;")
                                             .arg(msg->level >= 40 ? Theme::Red : Theme::Amber));
    }
}

void HMIWindow::publishCmdVel(double linear_x, double angular_z)
{
    geometry_msgs::msg::Twist twist_msg;
    twist_msg.linear.x = linear_x;
    twist_msg.angular.z = angular_z;
    cmd_vel_pub_->publish(twist_msg);
}

void HMIWindow::openCustomTaskDialog()
{
    TaskDialog dialog(this);
    if (dialog.exec() == QDialog::Accepted) {
        const QString taskText = dialog.getTaskText();
        if (!taskText.isEmpty()) publishPrompt(taskText.toStdString());
    }
}
