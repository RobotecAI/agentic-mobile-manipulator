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

#include <QColor>
#include <QString>

// Central design tokens + global stylesheet for the HMI.
// The look is a warm, light "control-room" theme: paper background, white
// cards with soft borders, deep-navy header strips, a rust primary action
// colour and traffic-light status colours.
namespace Theme {

// ---- Surfaces ----
inline constexpr const char* Bg          = "#f1efe8"; // app background (warm paper)
inline constexpr const char* Card        = "#ffffff"; // card surface
inline constexpr const char* CardAlt     = "#faf8f3"; // subtle inset surface
inline constexpr const char* Border      = "#e4e1d8"; // hairline border
inline constexpr const char* BorderHard  = "#d6d2c6"; // stronger border / inputs

// ---- Ink ----
inline constexpr const char* Ink         = "#1b2330"; // primary text
inline constexpr const char* Ink2        = "#586273"; // secondary text
inline constexpr const char* Muted       = "#9ba0a6"; // placeholders / em-dash
inline constexpr const char* Label       = "#9a9281"; // uppercase section labels

// ---- Navy (header strips / hero bars) ----
inline constexpr const char* Navy        = "#112a45";
inline constexpr const char* NavyTop     = "#17375a";
inline constexpr const char* NavyInk     = "#eaf1f8";
inline constexpr const char* NavyMuted   = "#90a6bd";
inline constexpr const char* NavyLine    = "#26456a";

// ---- Accents ----
inline constexpr const char* Blue        = "#2f6feb";
inline constexpr const char* Rust        = "#b8501d";
inline constexpr const char* RustHover   = "#9f4317";
inline constexpr const char* Green       = "#2fa45f";
inline constexpr const char* Amber       = "#e0a012";
inline constexpr const char* Red         = "#d6403a";

// ---- Misc ----
inline constexpr const char* Track       = "#e9e6dd"; // progress track

inline QColor c(const char* hex) { return QColor(QString::fromLatin1(hex)); }

// Returns the colour for a 0..100 utilisation value (green / amber / red).
inline QColor loadColor(double pct)
{
    if (pct >= 85.0) return c(Red);
    if (pct >= 60.0) return c(Amber);
    return c(Green);
}

// The application-wide stylesheet.
inline QString styleSheet()
{
    return QString(R"QSS(
/* ---------------- base ---------------- */
#centralRoot { background: %BG%; }
QWidget { font-size: 14px; }
QLabel { color: %INK%; background: transparent; }
QToolTip { background: %NAVY%; color: %NAVYINK%; border: none; padding: 6px 8px; border-radius: 6px; }

/* ---------------- header ---------------- */
#appHeader { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %NAVYTOP%, stop:1 %NAVY%); }
#appTitle { color: %NAVYINK%; font-size: 18px; font-weight: 700; }
#appSubtitle { color: %NAVYMUTED%; font-size: 12px; }

/* ---------------- tabs ---------------- */
QTabWidget::pane { border: none; background: transparent; top: -1px; }
QTabBar { background: transparent; qproperty-drawBase: 0; }
QTabBar::tab {
    background: transparent;
    color: %INK2%;
    padding: 10px 20px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 15px;
}
QTabBar::tab:selected { color: %INK%; border-bottom: 2px solid %BLUE%; font-weight: 600; }
QTabBar::tab:hover:!selected { color: %INK%; }

/* ---------------- cards ---------------- */
QFrame[role="card"]  { background: %CARD%; border: 1px solid %BORDER%; border-radius: 12px; }
QFrame[role="inset"] { background: %CARDALT%; border: 1px solid %BORDER%; border-radius: 10px; }
QFrame[role="navy"]  { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %NAVYTOP%, stop:1 %NAVY%); border: none; border-radius: 12px; }
QFrame[role="info"]  { background: #eef4fe; border: 1px solid #d4e2fb; border-radius: 12px; }

/* ---------------- buttons ---------------- */
QPushButton {
    background: %CARD%;
    color: %INK%;
    border: 1px solid %BORDERHARD%;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 14px;
}
QPushButton:hover { background: %CARDALT%; border-color: #c4bfb0; }
QPushButton:pressed { background: #efece4; }
QPushButton:disabled { color: %MUTED%; background: %CARDALT%; border-color: %BORDER%; }

QPushButton[variant="primary"] {
    background: %RUST%; color: #ffffff; border: none; font-weight: 600; padding: 12px 18px;
}
QPushButton[variant="primary"]:hover { background: %RUSTHOVER%; }
QPushButton[variant="primary"]:pressed { background: #8a3a14; }

QPushButton[variant="accent"] {
    background: %BLUE%; color: #ffffff; border: none; font-weight: 600;
}
QPushButton[variant="accent"]:hover { background: #245fd6; }

QPushButton[variant="ghost"] { background: transparent; border: 1px solid %BORDERHARD%; }
QPushButton[variant="ghost"]:hover { background: rgba(0,0,0,0.04); }

QPushButton[variant="link"] {
    background: transparent; border: none; color: %BLUE%; padding: 4px 2px; text-align: left;
}
QPushButton[variant="link"]:hover { color: #1b54c4; }

QPushButton#StopButton {
    background: %RED%; color: #ffffff; border: none; border-radius: 8px;
    font-size: 14px; font-weight: 700; padding: 9px 20px;
}
QPushButton#StopButton:hover { background: #bb302b; }
QPushButton#StopButton:pressed { background: #9c2622; }

/* camera selector pills */
QPushButton[variant="camsel"] {
    background: %CARDALT%; border: 1px solid %BORDERHARD%; border-radius: 6px;
    min-width: 26px; max-width: 30px; padding: 4px 0; font-weight: 600;
}
QPushButton[variant="camsel"][active="true"] { background: %GREEN%; color: #ffffff; border-color: %GREEN%; }

/* teleop d-pad */
QPushButton[variant="teleop"] {
    background: %CARD%; border: 1px solid %BORDERHARD%; border-radius: 10px;
    min-width: 56px; min-height: 48px;
}
QPushButton[variant="teleop"]:hover { background: %CARDALT%; }
QPushButton[variant="teleop"]:pressed { background: #e7f0ff; border-color: %BLUE%; }

/* ---------------- inputs ---------------- */
QLineEdit, QPlainTextEdit, QTextEdit {
    background: %CARD%; border: 1px solid %BORDERHARD%; border-radius: 8px;
    padding: 9px 12px; font-size: 14px; color: %INK%;
    selection-background-color: %BLUE%; selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid %BLUE%; }

QCheckBox { color: %INK%; spacing: 8px; font-size: 14px; padding: 2px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid %BORDERHARD%; border-radius: 5px; background: %CARD%; }
QCheckBox::indicator:hover { border-color: %BLUE%; }
QCheckBox::indicator:checked { background: %BLUE%; border-color: %BLUE%; image: url(:/icons/Check.svg); }

/* ---------------- lists / logs ---------------- */
QListWidget {
    background: transparent; border: none; font-size: 12px;
    font-family: "DejaVu Sans Mono", "Consolas", monospace;
}
QListWidget::item { padding: 3px 6px; border-bottom: 1px solid %BORDER%; }

/* ---------------- scrollbars ---------------- */
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cfcabb; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #b9b4a4; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #cfcabb; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* graphics views (camera / map tiles) */
QGraphicsView { background: #0e1622; border: 1px solid %BORDER%; border-radius: 8px; }
)QSS")
        .replace("%BG%", Bg)
        .replace("%CARD%", Card)
        .replace("%CARDALT%", CardAlt)
        .replace("%BORDERHARD%", BorderHard)
        .replace("%BORDER%", Border)
        .replace("%INK2%", Ink2)
        .replace("%INK%", Ink)
        .replace("%MUTED%", Muted)
        .replace("%NAVYTOP%", NavyTop)
        .replace("%NAVYINK%", NavyInk)
        .replace("%NAVYMUTED%", NavyMuted)
        .replace("%NAVY%", Navy)
        .replace("%RUSTHOVER%", RustHover)
        .replace("%RUST%", Rust)
        .replace("%BLUE%", Blue)
        .replace("%GREEN%", Green)
        .replace("%RED%", Red);
}

} // namespace Theme
