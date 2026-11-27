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

#include "AgentEventModel.h"

#include <QDateTime>

namespace {
// A message counts as still streaming while chunks keep arriving within this window.
constexpr qint64 kStreamingWindowMs = 1500;
}

AgentEventModel::AgentEventModel(QObject *parent) : QAbstractListModel(parent)
{
    clock_.start();
    epochMs_ = QDateTime::currentMSecsSinceEpoch();
}

int AgentEventModel::rowCount(const QModelIndex &parent) const
{
    return parent.isValid() ? 0 : events_.size();
}

QVariant AgentEventModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= events_.size()) {
        return {};
    }
    const AgentEvent &e = events_.at(index.row());
    switch (role) {
    case AgentRole: return e.agent;
    case NodeRole: return e.node;
    case KindRole: return e.kind;
    case TextRole: return e.text;
    case ToolNameRole: return e.toolName;
    case ImageRole: return e.image;
    case TaskRole: return e.task;
    case StartRole: return e.startMs;
    case EndRole: return e.endMs;
    case TimeRole: return QDateTime::fromMSecsSinceEpoch(epochMs_ + e.startMs).toString("HH:mm:ss");
    case DurationRole: return e.endMs - e.startMs;
    case StreamingRole:
        return (e.kind == "text" || e.kind == "thinking") && clock_.elapsed() - e.endMs < kStreamingWindowMs;
    case ResultRole: return e.result;
    case StatusRole: return e.status;
    case TokensRole: return e.tokens;
    default: return {};
    }
}

QHash<int, QByteArray> AgentEventModel::roleNames() const
{
    return {
        {AgentRole, "agent"},       {NodeRole, "node"},   {KindRole, "kind"},
        {TextRole, "text"},         {ToolNameRole, "toolName"}, {ImageRole, "image"},
        {TaskRole, "task"},         {StartRole, "startMs"}, {EndRole, "endMs"},
        {TimeRole, "time"},         {DurationRole, "durationMs"}, {StreamingRole, "streaming"},
        {ResultRole, "result"},     {StatusRole, "status"}, {TokensRole, "tokens"},
    };
}

void AgentEventModel::appendChunk(const QString &commId, const QString &agent, const QString &node,
                                  const QString &kind, const QString &chunk, const QString &task)
{
    const qint64 now = clock_.elapsed();
    // The newest event with this id and kind is the one being streamed.
    for (int row = events_.size() - 1; row >= 0 && row >= events_.size() - 8; --row) {
        AgentEvent &e = events_[row];
        if (e.kind == kind && e.commId == commId) {
            e.text += chunk;
            e.endMs = now;
            const QModelIndex idx = index(row);
            emit dataChanged(idx, idx, {TextRole, EndRole, DurationRole, StreamingRole});
            return;
        }
    }
    AgentEvent e;
    e.agent = agent;
    e.node = node;
    e.commId = commId;
    e.kind = kind;
    e.text = chunk;
    e.task = task;
    e.startMs = now;
    e.endMs = now;
    addEvent(e);
}

void AgentEventModel::addEvent(AgentEvent event)
{
    if (event.startMs == 0) {
        event.startMs = event.endMs = clock_.elapsed();
    }
    if (events_.size() >= maxEvents_) {
        beginRemoveRows(QModelIndex(), 0, 0);
        events_.removeFirst();
        endRemoveRows();
    }
    beginInsertRows(QModelIndex(), events_.size(), events_.size());
    events_.append(event);
    endInsertRows();
    emit countChanged();
}

bool AgentEventModel::update(const QString &commId, const std::function<void(AgentEvent &)> &change)
{
    for (int row = events_.size() - 1; row >= 0; --row) {
        if (events_[row].commId == commId) {
            change(events_[row]);
            emit dataChanged(index(row), index(row));
            return true;
        }
    }
    return false;
}

void AgentEventModel::updateLastOfNode(const QString &node, const std::function<void(AgentEvent &)> &change)
{
    for (int row = events_.size() - 1; row >= 0 && row >= events_.size() - 20; --row) {
        AgentEvent &e = events_[row];
        if (e.node == node && (e.kind == "text" || e.kind == "thinking")) {
            change(e);
            emit dataChanged(index(row), index(row));
            return;
        }
    }
}

QVariantMap AgentEventModel::get(int row) const
{
    QVariantMap map;
    if (row < 0 || row >= events_.size()) {
        return map;
    }
    const auto names = roleNames();
    for (auto it = names.cbegin(); it != names.cend(); ++it) {
        map[QString::fromUtf8(it.value())] = data(index(row), it.key());
    }
    return map;
}

void AgentEventModel::clear()
{
    beginResetModel();
    events_.clear();
    endResetModel();
    emit countChanged();
}

void AgentEventModel::refreshStreaming()
{
    // Only the last few events can still be streaming.
    const int first = std::max(0, static_cast<int>(events_.size()) - 8);
    if (first < events_.size()) {
        emit dataChanged(index(first), index(events_.size() - 1), {StreamingRole});
    }
}

AgentFilterModel::AgentFilterModel(QObject *parent) : QSortFilterProxyModel(parent)
{
    connect(this, &QAbstractItemModel::rowsInserted, this, &AgentFilterModel::countChanged);
    connect(this, &QAbstractItemModel::rowsRemoved, this, &AgentFilterModel::countChanged);
    connect(this, &QAbstractItemModel::modelReset, this, &AgentFilterModel::countChanged);
}

void AgentFilterModel::setAgent(const QString &agent)
{
    if (agent == agent_) {
        return;
    }
    agent_ = agent;
    invalidateFilter();
    emit agentChanged();
    emit countChanged();
}

void AgentFilterModel::setMinStartMs(qreal ms)
{
    if (qFuzzyCompare(ms + 1, minStartMs_ + 1)) {
        return;
    }
    minStartMs_ = ms;
    invalidateFilter();
    emit minStartMsChanged();
    emit countChanged();
}

QVariantMap AgentFilterModel::get(int row) const
{
    auto *model = qobject_cast<AgentEventModel *>(sourceModel());
    if (!model) {
        return {};
    }
    return model->get(mapToSource(index(row, 0)).row());
}

bool AgentFilterModel::filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const
{
    const QModelIndex idx = sourceModel()->index(sourceRow, 0, sourceParent);
    if (minStartMs_ > 0 && idx.data(AgentEventModel::StartRole).toLongLong() < minStartMs_) {
        return false;
    }
    return agent_.isEmpty() || idx.data(AgentEventModel::AgentRole).toString() == agent_;
}
