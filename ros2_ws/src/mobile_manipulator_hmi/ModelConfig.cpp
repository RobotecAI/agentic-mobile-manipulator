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

#include "ModelConfig.h"

#include <QStringList>
#include <toml++/toml.h>

QString defaultModelConfigPath()
{
    const QString demoRoot = qEnvironmentVariable("DEMO_ROOT");
    if (!demoRoot.isEmpty()) {
        return demoRoot + "/config.toml";
    }
    return QStringLiteral("config.toml");
}

ModelNames loadModelNames(const QString &configPath)
{
    ModelNames names{QStringLiteral("unknown"), QStringLiteral("unknown")};

    toml::table config;
    try {
        config = toml::parse_file(configPath.toStdString());
    } catch (const std::exception &) {
        return names;
    }

    const toml::table *endpoints = config["endpoints"].as_table();
    if (!endpoints) {
        return names;
    }

    // LLM: the endpoint referenced by [general].llm
    if (auto llmRef = config["general"]["llm"].value<std::string>()) {
        if (auto model = (*endpoints)[*llmRef]["model"].value<std::string>()) {
            names.llm = QString::fromStdString(*model);
        }
    }

    // VLM: every distinct model served by an endpoint of type "vlm"
    QStringList vlmModels;
    for (const auto &[endpointName, node] : *endpoints) {
        const toml::table *endpoint = node.as_table();
        if (!endpoint || (*endpoint)["type"].value_or(std::string{}) != "vlm") {
            continue;
        }
        if (auto model = (*endpoint)["model"].value<std::string>()) {
            const QString modelName = QString::fromStdString(*model);
            if (!vlmModels.contains(modelName)) {
                vlmModels << modelName;
            }
        }
    }
    if (!vlmModels.isEmpty()) {
        names.vlm = vlmModels.join(QStringLiteral(" | "));
    }

    return names;
}

QVector<Endpoint> loadEndpoints(const QString &configPath)
{
    QVector<Endpoint> result;
    toml::table config;
    try {
        config = toml::parse_file(configPath.toStdString());
    } catch (const std::exception &) {
        return result;
    }
    const toml::table *endpoints = config["endpoints"].as_table();
    if (!endpoints) {
        return result;
    }
    for (const auto &[name, node] : *endpoints) {
        const toml::table *ep = node.as_table();
        if (!ep) {
            continue;
        }
        Endpoint e;
        e.name = QString::fromStdString(std::string(name.str()));
        e.type = QString::fromStdString((*ep)["type"].value_or(std::string{}));
        e.backend = QString::fromStdString((*ep)["backend"].value_or(std::string{}));
        e.model = QString::fromStdString((*ep)["model"].value_or(std::string{}));
        e.host = QString::fromStdString((*ep)["host"].value_or(std::string{"localhost"}));
        e.port = static_cast<int>((*ep)["port"].value_or(int64_t{0}));
        if ((e.backend == "gpu" || e.backend == "cpu" || e.backend == "npu") && e.port > 0) {
            result.append(e);
        }
    }
    return result;
}
