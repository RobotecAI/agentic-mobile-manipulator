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
