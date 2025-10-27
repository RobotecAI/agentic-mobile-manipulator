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

#include "Config.h"
#include "LogView.h"
#include <QSpacerItem>
#include <QLayoutItem>
#include <QScroller>
#include <QScrollerProperties>
#include <QScrollArea>
#include <QScrollBar>

LogView::LogView(QWidget* parent)
    : QWidget(parent)
{
    m_scroll = new QScrollArea(this);
    m_scroll->setMaximumHeight(600);
    m_scroll->setMinimumHeight(600);
    m_scroll->setWidgetResizable(true);
    m_scroll->setFrameShape(QFrame::NoFrame);
    m_scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_scroll->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOn);
    m_scroll->setStyleSheet(
    "QScrollBar:vertical {"
    "    width: 24px;"
    "    background: transparent;"
    "    margin: 0;"
    "}"
    "QScrollBar::handle:vertical {"
    "    background: #888;"
    "    min-height: 30px;"
    "    border-radius: 6px;"
    "}"
    "QScrollBar::handle:vertical:hover {"
    "    background: #666;"
    "}"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
    "    height: 0px;"               // hide arrow buttons
    "}"
    );

    m_container = new QWidget(m_scroll);
    m_vbox = new QVBoxLayout(m_container);
    m_vbox->setContentsMargins(0, 0, 0, 0);
    m_vbox->setSpacing(2);
    m_vbox->addStretch(1);
    m_scroll->setMaximumHeight(800);
    m_scroll->setWidget(m_container);

    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->addWidget(m_scroll);

    // 🔑 Enable kinetic/touch scrolling
    QScroller::grabGesture(m_scroll->viewport(), QScroller::LeftMouseButtonGesture);

    // (Optional) Fine-tune scroll physics
    QScroller* scroller = QScroller::scroller(m_scroll->viewport());
    QScrollerProperties props = scroller->scrollerProperties();
    props.setScrollMetric(QScrollerProperties::DecelerationFactor, 0.15);
    props.setScrollMetric(QScrollerProperties::MaximumVelocity, 0.4);
    scroller->setScrollerProperties(props);
}


void LogView::addItem(LogItemWidget* item)
{
    if (!item) return;

    const bool atBottom = isAtBottom();


    // Insert before the final stretch
    // int insertIndex = m_vbox->count() - 1;
    m_vbox->insertWidget(0, item);
    m_items.emplace_back(item);

    evictIfNeeded();
}

void LogView::addLog(const demo_msgs::msg::VlmDescription& msg, const QColor& bg)
{
    // Adapt these fields to your custom message definition
    // const QString text = QString::fromStdString(msg.text);        // e.g. msg.text
    // #LogItemWidget* w = new LogItemWidget(text, image, bg, m_container);
    // addItem(w);
}

void LogView::onLogEnqueued(const demo_msgs::msg::VlmDescription& msg)
{
    addLog(msg);
}

void LogView::clear()
{
    // Remove all widgets (except the final stretch)
    for (auto& p : m_items) {
        if (p) {
            p->deleteLater();
        }
    }
    m_items.clear();
}

bool LogView::isAtBottom(int thresholdPx) const
{
    auto* sb = m_scroll->verticalScrollBar();
    return (sb->maximum() - sb->value()) <= thresholdPx;
}


void LogView::scrollToBottom() {
   if (auto* sb = m_scroll->verticalScrollBar())
       sb->setValue(sb->maximum());
}

void LogView::evictIfNeeded()
{
    while (m_items.size() > HardcodedConfig::MaxVLMMessages) {
        // Oldest item is at front
        QPointer<LogItemWidget> oldest = m_items.back();
        m_items.pop_back();
        if (oldest) {
            oldest->deleteLater();
        }
    }
}

