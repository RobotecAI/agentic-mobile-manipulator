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

