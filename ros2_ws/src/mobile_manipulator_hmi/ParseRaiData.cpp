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

#include "ParseRaiData.h"
#include <nlohmann/json.hpp>

namespace ParseRaiData
{

    std::optional<HRIMessage> parseHRIMessage(const QString& data)
    {
        namespace json = nlohmann;

        const auto j = json::json::parse(data.toStdString(), nullptr, false);
        if (!j.is_object())
        {
            return std::nullopt;
        }
        HRIMessage message;

        if (j.contains("type") && j["type"].is_string())
        {
            message.type_ = QString::fromStdString(j["type"].get<std::string>());
        }
        if (j.contains("tool_name") && j["tool_name"].is_string())
        {
            message.tool_name_ = QString::fromStdString(j["tool_name"].get<std::string>());
        }
        if (j.contains("tool_call") && j["tool_call"].is_string())
        {
            message.tool_call_ = QString::fromStdString(j["tool_call"].get<std::string>());
        }
        if (j.contains("tool_args") && j["tool_args"].is_object())
        {
            for (auto& [key, value] : j["tool_args"].items())
            {
                if (value.is_string())
                {
                    const auto qk = QString::fromStdString(key);
                    const auto qv = QString::fromStdString(value);
                    message.parameters_[qk] = qv;
                }
            }
        }


        return message;
    }
} // namespace PasrseRaiData
