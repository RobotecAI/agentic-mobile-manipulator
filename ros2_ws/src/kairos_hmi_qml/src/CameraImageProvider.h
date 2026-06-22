// Copyright (C) 2025 Robotec.ai sp. z o.o. — Apache-2.0
#pragma once

#include <QQuickImageProvider>
#include "RosBridge.h"

// Serves camera frames and the rendered map to QML Image elements via
// "image://kairos/<name>?<rev>" (the ?rev query forces a reload each frame).
class KairosImageProvider : public QQuickImageProvider
{
public:
    explicit KairosImageProvider(RosBridge* bridge)
        : QQuickImageProvider(QQuickImageProvider::Image), bridge_(bridge) {}

    QImage requestImage(const QString& id, QSize* size, const QSize& requested) override
    {
        Q_UNUSED(requested);
        const QString name = id.section('?', 0, 0);
        QImage img = (name == "map") ? bridge_->mapImage() : bridge_->cameraImage(name);
        if (img.isNull()) {
            img = QImage(2, 2, QImage::Format_ARGB32);
            img.fill(Qt::transparent);
        }
        if (size) *size = img.size();
        // Return native-resolution frames; QML's Image scales them on the GPU.
        // (Scaling to `requested` here can allocate huge buffers during layout.)
        return img;
    }

private:
    RosBridge* bridge_;
};
