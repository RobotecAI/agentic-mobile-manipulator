// Copyright (C) 2025 Robotec.ai sp. z o.o. — Apache-2.0
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QIcon>

#include "RosBridge.h"
#include "CameraImageProvider.h"

int main(int argc, char* argv[])
{
    QGuiApplication app(argc, argv);
    app.setApplicationName("Kairos+ Command");
    app.setOrganizationName("Robotec.ai");

    RosBridge bridge;

    int initialTab = 0;
    if (const char* t = qgetenv("KAIROS_TAB").constData(); t && *t) initialTab = atoi(t);
    // fullscreen by default (16:9 kiosk target); KAIROS_WINDOWED=1 for desktop dev
    const bool startFullscreen = qEnvironmentVariableIsEmpty("KAIROS_WINDOWED");

    QQmlApplicationEngine engine;
    engine.addImageProvider(QStringLiteral("kairos"), new KairosImageProvider(&bridge));
    engine.rootContext()->setContextProperty(QStringLiteral("ros"), &bridge);
    engine.rootContext()->setContextProperty(QStringLiteral("initialTab"), initialTab);
    engine.rootContext()->setContextProperty(QStringLiteral("startFullscreen"), startFullscreen);
    engine.load(QUrl(QStringLiteral("qrc:/qml/Main.qml")));
    if (engine.rootObjects().isEmpty()) return -1;

    return app.exec();
}
