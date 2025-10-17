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

