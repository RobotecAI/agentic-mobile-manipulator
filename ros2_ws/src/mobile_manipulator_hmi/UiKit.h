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

#include <QFrame>
#include <QString>

class QLabel;
class QVBoxLayout;
class QBoxLayout;

namespace ui {

// A small uppercase, letter-spaced section label (e.g. "SYSTEM RESOURCES").
QLabel* sectionLabel(const QString& text, bool onDark = false);

// A muted helper / caption label.
QLabel* captionLabel(const QString& text, bool onDark = false);

// A rounded "card" container. If a title is given an uppercase section label
// is added at the top. Use body() to populate the content area.
class Card : public QFrame
{
    Q_OBJECT
public:
    enum Style { Surface, Inset, Navy, Info };
    explicit Card(const QString& title = QString(), Style style = Surface, QWidget* parent = nullptr);
    QVBoxLayout* body() const { return body_; }
    void addTitle(const QString& text);

private:
    QVBoxLayout* body_ {nullptr};
    bool dark_ {false};
};

// A labelled horizontal utilisation bar (name on the left, value on the right,
// a rounded coloured track below). Used for CPU / RAM / GPU / DISK / VRAM.
class StatBar : public QWidget
{
    Q_OBJECT
public:
    explicit StatBar(const QString& name, QWidget* parent = nullptr, bool onDark = false);
    // value 0..100. Pass hasData=false to show an em-dash and empty track.
    void setValue(double pct, const QString& valueText = QString());
    void clearValue();

protected:
    void paintEvent(QPaintEvent*) override;

private:
    QLabel* name_ {nullptr};
    QLabel* value_ {nullptr};
    double pct_ {0.0};
    bool hasData_ {false};
    bool onDark_ {false};
};

// A status dot + label ("Nav2  ● down").
class StatusPill : public QWidget
{
    Q_OBJECT
public:
    enum State { Unknown, Ok, Warn, Bad, Idle };
    explicit StatusPill(QWidget* parent = nullptr, bool onDark = false);
    void setState(State s, const QString& text);

protected:
    void paintEvent(QPaintEvent*) override;

private:
    State state_ {Unknown};
    QString text_;
    bool onDark_ {false};
};

// A big-number tile: small uppercase caption above, large value below.
// Used for session stats and the mission status strip.
class StatTile : public QFrame
{
    Q_OBJECT
public:
    explicit StatTile(const QString& caption, QWidget* parent = nullptr, bool onDark = false);
    void setValue(const QString& v);
    void setAccent(const QString& cssColor);

private:
    QLabel* caption_ {nullptr};
    QLabel* value_ {nullptr};
};

// A key/value row (label left, value right). Returns the value label via value().
class KeyValue : public QWidget
{
    Q_OBJECT
public:
    explicit KeyValue(const QString& key, const QString& value = "—",
                      QWidget* parent = nullptr, bool onDark = false, int indent = 0);
    void setValue(const QString& v);
    QLabel* valueLabel() const { return value_; }

private:
    QLabel* value_ {nullptr};
};

} // namespace ui
