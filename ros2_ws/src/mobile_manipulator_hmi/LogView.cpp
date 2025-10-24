#include "Config.h"
#include "LogView.h"
#include <QSpacerItem>
#include <QLayoutItem>

LogView::LogView(QWidget* parent)
    : QWidget(parent)
{
    m_scroll = new QScrollArea(this);
    m_scroll->setWidgetResizable(true);
    m_scroll->setFrameShape(QFrame::NoFrame);
    m_scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_scroll->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOn);

    m_container = new QWidget(m_scroll);
    m_vbox = new QVBoxLayout(m_container);
    m_vbox->setContentsMargins(0, 0, 0, 0);
    m_vbox->setSpacing(2);

    // A stretch at the end keeps items packed to the top cleanly
    m_vbox->addStretch(1);

    m_scroll->setWidget(m_container);

    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->addWidget(m_scroll);
}

void LogView::addItem(LogItemWidget* item)
{
    if (!item) return;

    const bool atBottom = isAtBottom();


    // Insert before the final stretch
    int insertIndex = m_vbox->count() - 1;
    m_vbox->insertWidget(insertIndex, item);
    m_items.emplace_back(item);

    evictIfNeeded();
    if(!atBottom) scrollToBottom();
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
        QPointer<LogItemWidget> oldest = m_items.front();
        m_items.pop_front();
        if (oldest) {
            oldest->deleteLater();
        }
    }
}

