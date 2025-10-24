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
