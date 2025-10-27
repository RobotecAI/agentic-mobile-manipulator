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

#include <QObject>
#include <QVector>
#include <QMutex>
#include <deque>
#include <cstddef>

#include "Config.h"
#include <demo_msgs/msg/vlm_description.hpp>

class LogQueue : public QObject
{
    Q_OBJECT
public:
    explicit LogQueue(QObject* parent = nullptr);

    // Enqueue a log. If full, drops the oldest to make space.
    // Thread-safe. Use from your ROS subscriber callback.
    void enqueue(const demo_msgs::msg::VlmDescription::SharedPtr& log);


    // Remove and return all items (cheap batch consumption for the UI).
    QVector<demo_msgs::msg::VlmDescription> drain();

    // Snapshot copy, non-destructive.
    QVector<demo_msgs::msg::VlmDescription> snapshot() const;

    // Introspection
    std::size_t size() const;
    bool empty() const { return size() == 0; }
    void clear();

signals:
    // Emitted after an item is added (post-eviction if any).
    void logEnqueued(const demo_msgs::msg::VlmDescription& log);

    void droppedOldest(std::size_t count);

private:
    mutable QMutex m_mutex;
    std::deque<demo_msgs::msg::VlmDescription> m_queue;
};

