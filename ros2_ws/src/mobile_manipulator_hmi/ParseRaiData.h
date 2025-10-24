#pragma once
#include <qmap.h>
#include <qmetatype.h>
#include <QString>
#include <optional>
namespace ParseRaiData
{

    struct HRIMessage
    {
        QString type_;
        QString tool_name_;
        QString tool_call_;
        QMap<QString, QString> parameters_;
    };

    //! Parse a HRIMessage from a string
    //! Expected format: ''type'': ''tool_call'', ''tool_name'': ''move_object_from_pose_to_inspection_area'', ''tool_args'': {}
    std::optional<HRIMessage> parseHRIMessage(const QString& data);

}
