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

