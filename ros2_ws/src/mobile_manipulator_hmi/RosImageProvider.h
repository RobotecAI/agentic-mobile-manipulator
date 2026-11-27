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

#include <QHash>
#include <QImage>
#include <QMutex>
#include <QQuickImageProvider>

// Serves the latest frames ("camera", "top", "map", "vlm/<n>") to QML as image://ros/<id>.
// QML appends "?<counter>" to force a reload; the query part is ignored here.
class RosImageProvider : public QQuickImageProvider
{
public:
    RosImageProvider() : QQuickImageProvider(QQuickImageProvider::Image) {}

    void setImage(const QString &id, const QImage &image)
    {
        QMutexLocker lock(&mutex_);
        images_[id] = image;
    }

    void remove(const QString &id)
    {
        QMutexLocker lock(&mutex_);
        images_.remove(id);
    }

    QImage requestImage(const QString &id, QSize *size, const QSize &requestedSize) override
    {
        QMutexLocker lock(&mutex_);
        QImage image = images_.value(id.section('?', 0, 0));
        if (image.isNull()) {
            image = QImage(16, 9, QImage::Format_RGB32);
            image.fill(QColor("#0E1219"));
        }
        if (size) {
            *size = image.size();
        }
        if (requestedSize.isValid() && !requestedSize.isEmpty()) {
            return image.scaled(requestedSize, Qt::KeepAspectRatio, Qt::SmoothTransformation);
        }
        return image;
    }

private:
    QMutex mutex_;
    QHash<QString, QImage> images_;
};
