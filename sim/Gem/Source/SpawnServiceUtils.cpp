// NOTE: this file is a slightly modified copy of SimulationInterfaces/Code/Source/Services/SpawnServiceUtils.cpp

/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#include "SpawnServiceUtils.h"
#include <AzCore/std/string/regex.h>
#include <AzCore/std/string/string.h>
#include <AzCore/Component/TransformBus.h>
#include <AzCore/Component/ComponentApplicationBus.h>
#include <SimulationInterfaces/SimulationEntityManagerRequestBus.h>

namespace MobileManipulatorDemo::SpawnServiceUtils
{
    bool ValidateEntityName(AZStd::string_view entityName)
    {
        static const AZStd::regex entityRegex{
            R"(^[a-zA-Z0-9_]+$)"
        }; // Entity names can only contain alphanumeric characters and underscores
        return AZStd::regex_match(entityName.begin(), entityName.end(), entityRegex);
    }

    bool ValidateNamespaceName(AZStd::string_view namespaceName)
    {
        static const AZStd::regex namespaceRegex{
            R"(^[a-zA-Z0-9_/]+$)"
        }; // Namespace names can only contain alphanumeric characters and forward slashes
        return AZStd::regex_match(namespaceName.begin(), namespaceName.end(), namespaceRegex);
    }

    AZ::Outcome<void, AZStd::string> ValidateTransformNormalized(
        const AZ::Transform& transform, float quaternionTolerance, float maxTranslation)
    {
        // Check rotation quaternion is normalised.
        const float quaternionLength = transform.GetRotation().GetLength();
        if (!AZ::IsClose(quaternionLength, 1.0f, quaternionTolerance))
        {
            return AZ::Failure<AZStd::string>("Invalid pose orientation quaternion: length is not close to 1.0.");
        }

        // Check translation components are finite and within range.
        const AZ::Vector3 translation = transform.GetTranslation();
        if (!translation.IsFinite())
        {
            return AZ::Failure<AZStd::string>("Invalid pose translation: one or more components are NaN or infinite.");
        }
        const float absMax = translation.GetAbs().GetMaxElement();
        if (absMax > maxTranslation)
        {
            return AZ::Failure<AZStd::string>("Invalid pose translation: exceeds the maximum allowed.");
        }

        return AZ::Success();
    }

    AZStd::vector<AZ::EntityId> GetAllDescendants(AZ::EntityId parent)
    {
        AZStd::vector<AZ::EntityId> descendants;
        AZ::TransformBus::EventResult(
            descendants,
            parent,
            &AZ::TransformInterface::GetAllDescendants);

        return descendants;
    }

    AZStd::string GetEntityName(AZ::EntityId entityId)
    {
        AZStd::string name;
        AZ::ComponentApplicationBus::BroadcastResult(
            name,
            &AZ::ComponentApplicationRequests::GetEntityName,
            entityId
        );

        return name;
    }

    void RegisterChildGrippingPoints(const AZStd::string& rootName)
    {
        AZ::Outcome<AZ::EntityId, SimulationInterfaces::FailedResult> rootId;
        SimulationInterfaces::SimulationEntityManagerRequestBus::BroadcastResult(
            rootId,
            &SimulationInterfaces::SimulationEntityManagerRequests::GetEntityRoot,
            rootName
        );

        if (rootId.IsSuccess())
        {
            for (auto& descendantId : GetAllDescendants(rootId.GetValue()))
            {
                auto descendantName = GetEntityName(descendantId);

                if (descendantName.contains("GrippingPoint"))
                {
                    auto proposedName = rootName + "_" + descendantName;
                    AZ::Outcome<AZStd::string, SimulationInterfaces::FailedResult> result;
                    SimulationInterfaces::SimulationEntityManagerRequestBus::BroadcastResult(
                        result,
                        &SimulationInterfaces::SimulationEntityManagerRequests::RegisterNewSimulatedBody,
                        proposedName,
                        descendantId
                    );
                }
            }
        }
    }
} // namespace MobileManipulatorDemo::SpawnServiceUtils
