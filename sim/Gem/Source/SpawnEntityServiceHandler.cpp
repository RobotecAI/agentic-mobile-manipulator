// NOTE: this file is a slightly modified copy of SimulationInterfaces/Code/Source/Services/SpawnEntityServiceHandler.cpp

/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#include "SpawnEntityServiceHandler.h"
#include "AzCore/Component/ComponentApplicationBus.h"
#include "AzCore/Component/EntityId.h"
#include "AzCore/Component/TransformBus.h"
#include "AzCore/Debug/Trace.h"
#include "SimulationInterfaces/Result.h"
#include "SpawnServiceUtils.h"
#include <AzFramework/Physics/ShapeConfiguration.h>
#include <ROS2/ROS2Bus.h>
#include <ROS2/TF/TransformInterface.h>
#include <ROS2/Utilities/ROS2Conversions.h>
#include <SimulationInterfaces/RegistryUtils.h>
#include <SimulationInterfaces/SimulationEntityManagerRequestBus.h>
#include <SimulationInterfaces/ROS2SimulationInterfacesRequestBus.h>
#include <simulation_interfaces/msg/simulator_features.hpp>

namespace MobileManipulatorDemo
{
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

    SpawnEntityServiceHandler::SpawnEntityServiceHandler()
    {
        ROS2SimulationInterfaces::ROS2SimulationInterfacesRequestBus::Broadcast(
            &ROS2SimulationInterfaces::ROS2SimulationInterfacesRequests::AddSimulationFeatures,
            AZStd::unordered_set<ROS2SimulationInterfaces::SimulationFeatureType>{
                simulation_interfaces::msg::SimulatorFeatures::SPAWNING });
    }

    AZStd::optional<SpawnEntityServiceHandler::Response> SpawnEntityServiceHandler::HandleServiceRequest(
        const std::shared_ptr<rmw_request_id_t> header, const Request& request)
    {
        AZ_Printf("MobileManipulatorDemo", "Hello world!!! SpawnEntityServiceHandler");
        const AZStd::string_view name{ request.name.c_str(), request.name.size() };
#if SIMULATION_INTERFACES_MAJOR_API_VERSION >= 2
        const AZStd::string_view uri{ request.entity_resource.uri.c_str(), request.entity_resource.uri.size() };
#else
        const AZStd::string_view uri{ request.uri.c_str(), request.uri.size() };
#endif
        const AZStd::string_view entityNamespace{ request.entity_namespace.c_str(), request.entity_namespace.size() };
        const AZStd::string_view messageFrameId{ request.initial_pose.header.frame_id.c_str(),
                                                 request.initial_pose.header.frame_id.size() };
        const builtin_interfaces::msg::Time zeroTime = builtin_interfaces::msg::Time();

        // Validate entity name
        if (!name.empty() && !SpawnServiceUtils::ValidateEntityName(name))
        {
            Response response;
            response.result.result = simulation_interfaces::srv::SpawnEntity::Response::NAME_INVALID;
            response.result.error_message = "Invalid entity name. Entity names can only contain alphanumeric characters and underscores.";
            SendResponse(response);
            return AZStd::nullopt;
        }

        // Validate namespace name
        if (!entityNamespace.empty() && !SpawnServiceUtils::ValidateNamespaceName(entityNamespace))
        {
            Response response;
            response.result.result = simulation_interfaces::srv::SpawnEntity::Response::NAMESPACE_INVALID;
            response.result.error_message =
                "Invalid entity namespace. Entity namespaces can only contain alphanumeric characters and forward slashes.";
            SendResponse(response);
            return AZStd::nullopt;
        }

        // deal with frames
        const auto simulatorFrameId = ROS2SimulationInterfaces::RegistryUtilities::GetSimulatorROS2Frame();
        AZ::Transform transformOffset = AZ::Transform::CreateIdentity();
        if (!messageFrameId.empty() && simulatorFrameId != messageFrameId)
        {
            auto transformInterface = ROS2::TFInterface::Get();
            AZ_Assert(transformInterface, "TFInterface is not available, cannot set entity state without transform offset.");
            const auto transformOutcome = transformInterface->GetTransform(simulatorFrameId, messageFrameId, zeroTime);

            if (transformOutcome.IsSuccess())
            {
                transformOffset = transformOutcome.GetValue();
            }
            else
            {
                Response response;
                response.result.result = simulation_interfaces::msg::Result::RESULT_OPERATION_FAILED;
                response.result.error_message = transformOutcome.GetError().c_str();
                SendResponse(response);
                return AZStd::nullopt;
            }
        }

        const AZ::Transform requestedPose = ROS2::ROS2Conversions::FromROS2Pose(request.initial_pose.pose);
        if (const auto poseValidation = SpawnServiceUtils::ValidateTransformNormalized(requestedPose); !poseValidation.IsSuccess())
        {
            Response response;
            response.result.result = simulation_interfaces::srv::SpawnEntity::Response::INVALID_POSE;
            response.result.error_message = poseValidation.GetError().c_str();
            SendResponse(response);
            return AZStd::nullopt;
        }

        const AZ::Transform initialPose = transformOffset *
            AZ::Transform::CreateFromQuaternionAndTranslation(requestedPose.GetRotation().GetNormalized(), requestedPose.GetTranslation());

        SimulationInterfaces::PreInsertionCb preinsertionCB =
            [this](const AZ::Outcome<AzFramework::SpawnableEntityContainerView, SimulationInterfaces::FailedResult>& outcome)
        {
            if (!outcome.IsSuccess())
            {
                Response response;
                const auto& failedResult = outcome.GetError();
                response.result.result = failedResult.m_errorCode;
                response.result.error_message = failedResult.m_errorString.c_str();

                SendResponse(response);
            }
        };
        SimulationInterfaces::SimulationEntityManagerRequestBus::Broadcast(
            &SimulationInterfaces::SimulationEntityManagerRequests::SpawnEntity,
            name,
            uri,
            entityNamespace,
            initialPose,
            request.allow_renaming,
            preinsertionCB,
            [this](const AZ::Outcome<AZStd::string, SimulationInterfaces::FailedResult>& outcome)
            {
                Response response;
                if (outcome.IsSuccess())
                {
                    RegisterChildGrippingPoints(outcome.GetValue());
                    response.result.result = simulation_interfaces::msg::Result::RESULT_OK;
                    response.entity_name = outcome.GetValue().c_str();
                }
                else
                {
                    const auto& failedResult = outcome.GetError();
                    response.result.result = failedResult.m_errorCode;
                    response.result.error_message = failedResult.m_errorString.c_str();
                }
                SendResponse(response);
            });
        return AZStd::nullopt;
    }

} // namespace MobileManipulatorDemo
