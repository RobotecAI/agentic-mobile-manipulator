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

#include "LogQueue.h"

LogQueue::LogQueue(QObject* parent)
    : QObject(parent)
{
}

void LogQueue::enqueue(const demo_msgs::msg::VlmDescription::SharedPtr& log)
{
    demo_msgs::msg::VlmDescription latestCopy;
    std::size_t dropped = 0;

    {
        QMutexLocker locker(&m_mutex);

        if (m_queue.size() >= HardcodedConfig::MaxVLMMessages) {
            m_queue.pop_front();
            ++dropped;
        }

        m_queue.emplace_back(*log);          // copy from ROS SharedPtr
        latestCopy = m_queue.back();         // copy out for emission
    }

    if (dropped > 0)
        emit droppedOldest(dropped);

    emit logEnqueued(latestCopy);
}

QVector<demo_msgs::msg::VlmDescription> LogQueue::snapshot() const
{
    QMutexLocker locker(&m_mutex);
    QVector<demo_msgs::msg::VlmDescription> out;
    out.reserve(static_cast<int>(m_queue.size()));
    for (const auto& item : m_queue)
        out.push_back(item);
    return out;
}

std::size_t LogQueue::size() const
{
    QMutexLocker locker(&m_mutex);
    return m_queue.size();
}

void LogQueue::clear()
{
    QMutexLocker locker(&m_mutex);
    m_queue.clear();
}

