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

#include <QString>
#include <QVector>

struct ModelNames {
    QString llm;
    QString vlm;
};

// $DEMO_ROOT/config.toml when DEMO_ROOT is set, otherwise ./config.toml
// (which may be a symlink placed next to the HMI's working directory).
QString defaultModelConfigPath();

// Reads the inference SSOT (config.toml) and returns the model names to
// display. Never throws: a missing or malformed file yields "unknown".
ModelNames loadModelNames(const QString &configPath);

// One locally served inference endpoint ([endpoints.*] with backend gpu, cpu or npu).
struct Endpoint {
    QString name;
    QString type;
    QString backend;
    QString model;
    QString host;
    int port = 0;
};

// Every locally served endpoint in config.toml; empty on a missing or malformed file.
QVector<Endpoint> loadEndpoints(const QString &configPath);
