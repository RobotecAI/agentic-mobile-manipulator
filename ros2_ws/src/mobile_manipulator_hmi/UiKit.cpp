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

#include "UiKit.h"
#include "Theme.h"

#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPainter>
#include <QPainterPath>
#include <QFont>
#include <QVariant>
#include <algorithm>
#include <cmath>

namespace ui {

QLabel* sectionLabel(const QString& text, bool onDark)
{
    auto* l = new QLabel(text.toUpper());
    QFont f = l->font();
    f.setPointSizeF(std::max(7.5, f.pointSizeF() - 2.0));
    f.setBold(true);
    f.setLetterSpacing(QFont::AbsoluteSpacing, 1.1);
    l->setFont(f);
    l->setStyleSheet(QString("color:%1; background:transparent;")
                         .arg(onDark ? Theme::NavyMuted : Theme::Label));
    return l;
}

QLabel* captionLabel(const QString& text, bool onDark)
{
    auto* l = new QLabel(text);
    l->setWordWrap(true);
    QFont f = l->font();
    f.setPointSizeF(std::max(7.5, f.pointSizeF() - 1.0));
    l->setFont(f);
    l->setStyleSheet(QString("color:%1; background:transparent;")
                         .arg(onDark ? Theme::NavyMuted : Theme::Ink2));
    return l;
}

// ---------------- Card ----------------
Card::Card(const QString& title, Style style, QWidget* parent)
    : QFrame(parent)
{
    const char* role = "card";
    switch (style) {
        case Surface: role = "card"; break;
        case Inset:   role = "inset"; break;
        case Navy:    role = "navy"; dark_ = true; break;
        case Info:    role = "info"; break;
    }
    setProperty("role", QString::fromLatin1(role));
    body_ = new QVBoxLayout(this);
    body_->setContentsMargins(16, 14, 16, 16);
    body_->setSpacing(10);
    if (!title.isEmpty()) addTitle(title);
}

void Card::addTitle(const QString& text)
{
    body_->insertWidget(0, sectionLabel(text, dark_));
}

// ---------------- StatBar ----------------
StatBar::StatBar(const QString& name, QWidget* parent, bool onDark)
    : QWidget(parent), onDark_(onDark)
{
    auto* v = new QVBoxLayout(this);
    v->setContentsMargins(0, 0, 0, 0);
    v->setSpacing(6);

    auto* row = new QHBoxLayout();
    row->setContentsMargins(0, 0, 0, 0);
    name_ = new QLabel(name);
    name_->setStyleSheet(QString("color:%1; background:transparent; font-weight:600;")
                             .arg(onDark ? Theme::NavyInk : Theme::Ink));
    value_ = new QLabel("—");
    value_->setStyleSheet(QString("color:%1; background:transparent; font-weight:700;")
                              .arg(onDark ? Theme::NavyInk : Theme::Ink));
    value_->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    row->addWidget(name_);
    row->addStretch();
    row->addWidget(value_);
    v->addLayout(row);

    setMinimumHeight(40);
}

void StatBar::setValue(double pct, const QString& valueText)
{
    pct_ = std::clamp(pct, 0.0, 100.0);
    hasData_ = true;
    value_->setText(valueText.isEmpty() ? QString::number(std::lround(pct_)) + "%" : valueText);
    update();
}

void StatBar::clearValue()
{
    hasData_ = false;
    value_->setText("—");
    update();
}

void StatBar::paintEvent(QPaintEvent*)
{
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int barH = 8;
    const int y = height() - barH - 1;
    QRectF track(0, y, width(), barH);
    const double r = barH / 2.0;

    QColor trackCol = onDark_ ? QColor(255, 255, 255, 28) : Theme::c(Theme::Track);
    p.setPen(Qt::NoPen);
    p.setBrush(trackCol);
    p.drawRoundedRect(track, r, r);

    if (hasData_ && pct_ > 0.0) {
        double w = std::max(barH * 1.0, track.width() * pct_ / 100.0);
        QRectF fill(0, y, w, barH);
        p.setBrush(Theme::loadColor(pct_));
        p.drawRoundedRect(fill, r, r);
    }
}

// ---------------- StatusPill ----------------
StatusPill::StatusPill(QWidget* parent, bool onDark) : QWidget(parent), onDark_(onDark)
{
    setMinimumHeight(22);
}

void StatusPill::setState(State s, const QString& text)
{
    state_ = s;
    text_ = text;
    update();
}

void StatusPill::paintEvent(QPaintEvent*)
{
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    QColor dot;
    switch (state_) {
        case Ok:   dot = Theme::c(Theme::Green); break;
        case Warn: dot = Theme::c(Theme::Amber); break;
        case Bad:  dot = Theme::c(Theme::Red);   break;
        case Idle: dot = QColor("#b7bcc4");      break;
        default:   dot = QColor("#c9cdd3");      break;
    }

    const int d = 9;
    const int cy = height() / 2;
    p.setPen(Qt::NoPen);
    p.setBrush(dot);
    p.drawEllipse(QPointF(d / 2.0 + 1, cy), d / 2.0, d / 2.0);

    p.setPen(onDark_ ? Theme::c(Theme::NavyInk) : Theme::c(Theme::Ink2));
    p.setFont(font());
    QRect tr(d + 9, 0, width() - d - 9, height());
    p.drawText(tr, Qt::AlignVCenter | Qt::AlignLeft, text_);
}

// ---------------- StatTile ----------------
StatTile::StatTile(const QString& caption, QWidget* parent, bool onDark)
    : QFrame(parent)
{
    if (!onDark) setProperty("role", QStringLiteral("inset"));
    auto* v = new QVBoxLayout(this);
    v->setContentsMargins(14, 10, 14, 12);
    v->setSpacing(3);

    caption_ = sectionLabel(caption, onDark);
    value_ = new QLabel("—");
    QFont vf = value_->font();
    vf.setPointSizeF(vf.pointSizeF() + 9.0);
    vf.setBold(true);
    value_->setFont(vf);
    value_->setStyleSheet(QString("color:%1; background:transparent;")
                              .arg(onDark ? Theme::NavyInk : Theme::Ink));
    v->addWidget(caption_);
    v->addWidget(value_);
}

void StatTile::setValue(const QString& val) { value_->setText(val); }

void StatTile::setAccent(const QString& cssColor)
{
    value_->setStyleSheet(QString("color:%1; background:transparent;").arg(cssColor));
}

// ---------------- KeyValue ----------------
KeyValue::KeyValue(const QString& key, const QString& value, QWidget* parent, bool onDark, int indent)
    : QWidget(parent)
{
    auto* row = new QHBoxLayout(this);
    row->setContentsMargins(indent, 3, 0, 3);
    row->setSpacing(8);

    auto* k = new QLabel(key);
    k->setStyleSheet(QString("color:%1; background:transparent;")
                         .arg(onDark ? Theme::NavyMuted : Theme::Ink2));
    value_ = new QLabel(value);
    value_->setStyleSheet(QString("color:%1; background:transparent; font-weight:600;")
                              .arg(onDark ? Theme::NavyInk : Theme::Ink));
    value_->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    value_->setTextInteractionFlags(Qt::TextSelectableByMouse);

    row->addWidget(k);
    row->addStretch();
    row->addWidget(value_);
}

void KeyValue::setValue(const QString& v) { value_->setText(v); }

} // namespace ui
