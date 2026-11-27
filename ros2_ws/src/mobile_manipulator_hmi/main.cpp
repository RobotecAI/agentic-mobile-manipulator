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

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QQuickWindow>
#include <QTimer>

#include <rclcpp/rclcpp.hpp>

#include "RosBridge.h"
#include "RosImageProvider.h"

int main(int argc, char *argv[])
{
    QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    QGuiApplication app(argc, argv);
    app.setApplicationName("Mobile Manipulator HMI");
    QQuickStyle::setStyle("Default");
    rclcpp::init(argc, argv);

    int result = 0;
    {
        auto *images = new RosImageProvider();  // owned by the engine
        RosBridge ros(images);

        QQmlApplicationEngine engine;
        engine.addImageProvider("ros", images);
        engine.rootContext()->setContextProperty("ros", &ros);
        // HMI_FULLSCREEN=1 starts full screen (F11 toggles).
        engine.rootContext()->setContextProperty("startFullScreen", qEnvironmentVariableIsSet("HMI_FULLSCREEN"));
        engine.rootContext()->setContextProperty("startPage", qEnvironmentVariableIntValue("HMI_PAGE"));
        engine.load(QUrl(QStringLiteral("qrc:/qml/Main.qml")));
        if (engine.rootObjects().isEmpty()) {
            rclcpp::shutdown();
            return 1;
        }
        // HMI_SCREENSHOT=<file.png>: save the window after HMI_SCREENSHOT_MS (default 4000) and quit.
        // For headless checks: QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software.
        if (const QString shot = qEnvironmentVariable("HMI_SCREENSHOT"); !shot.isEmpty()) {
            auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().first());
            const int delay = qEnvironmentVariableIntValue("HMI_SCREENSHOT_MS");
            QTimer::singleShot(delay > 0 ? delay : 4000, &app, [window, shot]() {
                const QImage image = window->grabWindow();
                qInfo("HMI_SCREENSHOT %s: %dx%d saved=%d", qPrintable(shot), image.width(), image.height(), image.save(shot));
                QCoreApplication::quit();
            });
        }
        result = app.exec();
    }
    rclcpp::shutdown();
    return result;
}
