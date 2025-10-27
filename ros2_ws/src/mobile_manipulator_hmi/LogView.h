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

#pragma once

#include <QWidget>
#include <QVector>
#include <QPointer>
#include <QColor>
#include <deque>

#include <QScrollArea>
#include <QVBoxLayout>
#include <QScrollBar>

#include "LogItemWidget.h"
#include <demo_msgs/msg/vlm_description.hpp>

class LogView : public QWidget
{
    Q_OBJECT
public:
    explicit LogView(QWidget* parent = nullptr);

    // Add a prebuilt item widget (optional API)
    void addItem(LogItemWidget* item);

    // Convenience: create + add from a ros message
    void addLog(const demo_msgs::msg::VlmDescription& msg,
                const QColor& bg = QColor("#101418"));

public slots:
    // Slot compatible with LogQueue::logEnqueued(const demo_msgs::msg::VlmDescription&)
    void onLogEnqueued(const demo_msgs::msg::VlmDescription& msg);

    // Clear all items
    void clear();

private:
    bool isAtBottom(int thresholdPx = 8) const;
    void evictIfNeeded();
    void scrollToBottom();

private:
    QScrollArea*   m_scroll {nullptr};
    QWidget*       m_container {nullptr};
    QVBoxLayout*   m_vbox {nullptr};
    std::deque<QPointer<LogItemWidget>> m_items; // keep order, safe against deletes
};

