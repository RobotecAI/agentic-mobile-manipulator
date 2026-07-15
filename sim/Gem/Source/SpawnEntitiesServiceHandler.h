// NOTE: this file is a slightly modified copy of SimulationInterfaces/Code/Source/Services/SpawnEntitiesServiceHandler.h

/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#pragma once

#include "ROS2Service.h"
#include <AzCore/std/string/string_view.h>
#include <simulation_interfaces/srv/spawn_entities.hpp>

namespace MobileManipulatorDemo
{
    class SpawnEntitiesServiceHandler
        : public ROS2Service<simulation_interfaces::srv::SpawnEntities>
    {
    public:
        SpawnEntitiesServiceHandler();

        AZStd::string_view GetTypeName() const override
        {
            return "SpawnEntities";
        }

        AZStd::string_view GetDefaultName() const override
        {
            return "spawn_entities";
        }

        AZStd::optional<Response> HandleServiceRequest(const std::shared_ptr<rmw_request_id_t> header, const Request& request) override;
    };

} // namespace MobileManipulatorDemo
