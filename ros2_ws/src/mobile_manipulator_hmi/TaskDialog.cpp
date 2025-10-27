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

#include "TaskDialog.h"
#include <QApplication>
#include <QInputMethod>

TaskDialog::TaskDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("Send Custom Task");
    setModal(true);
    resize(400, 200);

    auto *mainLayout = new QVBoxLayout(this);

    // Title label
    auto *titleLabel = new QLabel("Enter task prompt for the robot:");
    titleLabel->setStyleSheet("font-weight: bold; margin-bottom: 5px;");
    mainLayout->addWidget(titleLabel);

    // Text edit for multiline input
    textEdit_ = new QTextEdit(this);
    textEdit_->setPlaceholderText("Type your task here...\nExample: Navigate to kitchen and pick up the bottle");
    textEdit_->setMaximumHeight(100);
    mainLayout->addWidget(textEdit_);

    // Button layout
    auto *buttonLayout = new QHBoxLayout();
    buttonLayout->addStretch();

    cancelButton_ = new QPushButton("Cancel", this);
    sendButton_ = new QPushButton("Send Task", this);
    sendButton_->setDefault(true);
    sendButton_->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }");

    buttonLayout->addWidget(cancelButton_);
    buttonLayout->addWidget(sendButton_);
    mainLayout->addLayout(buttonLayout);

    // Connect signals
    connect(sendButton_, &QPushButton::clicked, this, &TaskDialog::onSendClicked);
    connect(cancelButton_, &QPushButton::clicked, this, &TaskDialog::onCancelClicked);
    connect(this, &QDialog::done, this, &TaskDialog::hideOnScreenKeyboard);
    // Focus on text edit
    textEdit_->setFocus();
    showOnScreenKeyboard();
}

TaskDialog::~TaskDialog()
{
}

QString TaskDialog::getTaskText() const
{
    return textEdit_->toPlainText().trimmed();
}

void TaskDialog::onSendClicked()
{
    if (!textEdit_->toPlainText().trimmed().isEmpty()) {
        accept();
    }
    hideOnScreenKeyboard();
}

void TaskDialog::onCancelClicked()
{
    reject();
    hideOnScreenKeyboard();
}

void TaskDialog::showOnScreenKeyboard()
{
    if (!onScreenKeyboardProcess_ || onScreenKeyboardProcess_->state() != QProcess::Running) {
        onScreenKeyboardProcess_ = new QProcess(this);

        // Try different virtual keyboard commands based on what's available
        QStringList keyboards = {"onboard", "florence", "kvkbd", "xvkbd"};

        for (const QString &keyboard : keyboards) {
            onScreenKeyboardProcess_->start(keyboard);
            if (onScreenKeyboardProcess_->waitForStarted(1000)) {
                break;
            }
        }
    }
}

void TaskDialog::hideOnScreenKeyboard()
{
    if (onScreenKeyboardProcess_ && onScreenKeyboardProcess_->state() == QProcess::Running) {
        onScreenKeyboardProcess_->terminate();
        if (!onScreenKeyboardProcess_->waitForFinished(3000)) {
            onScreenKeyboardProcess_->kill();
        }
        onScreenKeyboardProcess_->deleteLater();
        onScreenKeyboardProcess_ = nullptr;
    }
}