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

#pragma once

#include <QAbstractListModel>
#include <QElapsedTimer>
#include <QSortFilterProxyModel>
#include <QString>
#include <QVector>

#include <functional>

// One entry of the agent stream: a streamed text message, a tool call, or a VLM
// finding. Text chunks with the same communication id are appended in place.
struct AgentEvent
{
    QString agent;     // display name ("Orchestrator", "Safety", ...)
    QString node;      // raw LangGraph node name, empty for VLM findings
    QString commId;    // "<node>:<run id>" for streamed messages
    QString kind;      // "text" | "tool" | "vlm"
    QString text;      // message text, tool arguments (pretty JSON) or VLM description
    QString toolName;
    QString image;     // image provider id for VLM findings, empty otherwise
    QString task;      // task the event belongs to
    QString result;    // tool output
    QString status;    // tools: "running" | "ok" | "error"
    QString tokens;    // "1.9k in · 214 out" when the agent reported usage
    qint64 startMs = 0;  // ms since the HMI started
    qint64 endMs = 0;
};

class AgentEventModel : public QAbstractListModel
{
    Q_OBJECT
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Roles {
        AgentRole = Qt::UserRole + 1,
        NodeRole,
        KindRole,
        TextRole,
        ToolNameRole,
        ImageRole,
        TaskRole,
        StartRole,
        EndRole,
        TimeRole,
        DurationRole,
        StreamingRole,
        ResultRole,
        StatusRole,
        TokensRole,
    };

    explicit AgentEventModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    // Streamed chunk (kind "text" or "thinking"): appended to the open event with the same
    // commId and kind, else a new event.
    void appendChunk(const QString &commId, const QString &agent, const QString &node,
                     const QString &kind, const QString &chunk, const QString &task);
    void addEvent(AgentEvent event);
    // Updates the newest event with this commId (e.g. a tool result). Returns false if none.
    bool update(const QString &commId, const std::function<void(AgentEvent &)> &change);
    // Updates the newest text/thinking event of a node (e.g. token usage from llm_end).
    void updateLastOfNode(const QString &node, const std::function<void(AgentEvent &)> &change);
    qint64 nowMs() const { return clock_.elapsed(); }

    Q_INVOKABLE QVariantMap get(int row) const;
    Q_INVOKABLE void clear();

    // Called periodically so "streaming" flags expire after a pause in the chunks.
    void refreshStreaming();

signals:
    void countChanged();

private:
    QVector<AgentEvent> events_;
    QElapsedTimer clock_;
    qint64 epochMs_ = 0;  // wall-clock time when clock_ started
    int maxEvents_ = 500;
};

// Filters the stream by agent name ("" = all). Used by the Mission and Agents pages.
class AgentFilterModel : public QSortFilterProxyModel
{
    Q_OBJECT
    Q_PROPERTY(QString agent READ agent WRITE setAgent NOTIFY agentChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    explicit AgentFilterModel(QObject *parent = nullptr);
    QString agent() const { return agent_; }
    void setAgent(const QString &agent);
    int count() const { return rowCount(); }
    Q_INVOKABLE QVariantMap get(int row) const;

signals:
    void agentChanged();
    void countChanged();

protected:
    bool filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const override;

private:
    QString agent_;
};
