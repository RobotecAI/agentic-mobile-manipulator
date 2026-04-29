
#include "TrackedBySimulationInterfacesComponent.h"
#include "AzCore/Component/ComponentBus.h"
#include "AzCore/Component/EntityId.h"
#include "AzCore/Component/TransformBus.h"
#include "AzCore/Debug/Trace.h"
#include "AzCore/Outcome/Outcome.h"
#include "AzCore/std/string/string.h"
#include "SimulationInterfaces/Result.h"

#include <AzCore/Serialization/SerializeContext.h>
#include <AzCore/Serialization/EditContext.h>
#include <AzCore/RTTI/BehaviorContext.h>

#include <SimulationInterfaces/SimulationEntityManagerRequestBus.h>

namespace MobileManipulatorDemo
{
    AZ_COMPONENT_IMPL(TrackedBySimulationInterfacesComponent, "TrackedBySimulationInterfacesComponent", "{74E33187-1402-4BAA-ABD9-C29728A036C6}");

    using SimulationInterfaces::SimulationEntityManagerRequestBus;
    using SimulationInterfaces::SimulationEntityManagerRequests;

    // Find the first ancestor of the given entity that has a simulated body name and return that name.
    // If no such ancestor is found, return empty string.
    AZStd::string GetParentName(AZ::Entity* entity)
    {
        auto* transformInterface = entity->GetTransform();
        if (!transformInterface)
        {
            return "";
        }
        AZ::EntityId parentId = transformInterface->GetParentId();
        if (!parentId.IsValid())
        {
            return "";
        }
        AZ::Outcome<AZStd::string, SimulationInterfaces::FailedResult> result;
        SimulationInterfaces::SimulationEntityManagerRequestBus::BroadcastResult(
            result,
            &SimulationEntityManagerRequests::GetSimulatedBodyNameById,
            parentId);
        if (result.IsSuccess())
        {
            return result.GetValue();
        }

        AZ::Entity* parentEntity = nullptr;
        AZ::ComponentApplicationBus::BroadcastResult(parentEntity, &AZ::ComponentApplicationRequests::FindEntity, parentId);
        if (!parentEntity)
        {
            return "";
        }

        return GetParentName(parentEntity);
    }

    void TrackedBySimulationInterfacesComponent::Activate()
    {
        TrackedBySimulationInterfacesRequestBus::Handler::BusConnect(GetEntityId());

        // We assign the name in OnTick because at the time of activation the parent's name is not yet registered.
        AZ::TickBus::Handler::BusConnect();
    }

    void TrackedBySimulationInterfacesComponent::Deactivate()
    {
        TrackedBySimulationInterfacesRequestBus::Handler::BusDisconnect(GetEntityId());

        if (m_registeredName.IsSuccess())
        {
            AZ::Outcome<void, SimulationInterfaces::FailedResult> error;
            SimulationEntityManagerRequestBus::BroadcastResult(
                error,
                &SimulationEntityManagerRequests::UnregisterSimulatedBody,
                m_registeredName.GetValue());
        }
    }

    void TrackedBySimulationInterfacesComponent::OnTick([[maybe_unused]] float deltaTime, [[maybe_unused]] AZ::ScriptTimePoint time)
    {
        if (!m_registeredName.IsSuccess())
        {
            SimulationEntityManagerRequestBus::BroadcastResult(
                m_registeredName,
                &SimulationEntityManagerRequests::RegisterNewSimulatedBody,
                GetParentName(GetEntity()) + "_" + GetEntity()->GetName(), GetEntityId());
            
            if (m_registeredName.IsSuccess())
            {
                AZ_Printf("MobileManipulatorDemo", "Registered entity for simulation interfaces as %s", m_registeredName.GetValue().c_str());
            }
            else
            {
                AZ_Printf("MobileManipulatorDemo", "Failed to register entity for simulation interfaces");
            }

            AZ::TickBus::Handler::BusDisconnect();
        }
    }

    void TrackedBySimulationInterfacesComponent::Reflect(AZ::ReflectContext* context)
    {
        if (auto serializeContext = azrtti_cast<AZ::SerializeContext*>(context))
        {
            serializeContext->Class<TrackedBySimulationInterfacesComponent, AZ::Component>()
                ->Version(1)
                ;

            if (AZ::EditContext* editContext = serializeContext->GetEditContext())
            {
                editContext->Class<TrackedBySimulationInterfacesComponent>("TrackedBySimulationInterfacesComponent", "[Description of functionality provided by this component]")
                    ->ClassElement(AZ::Edit::ClassElements::EditorData, "")
                    ->Attribute(AZ::Edit::Attributes::Category, "ComponentCategory")
                    ->Attribute(AZ::Edit::Attributes::Icon, "Icons/Components/Component_Placeholder.svg")
                    ->Attribute(AZ::Edit::Attributes::AppearsInAddComponentMenu, AZ_CRC_CE("Game"))
                    ;
            }
        }

        if (AZ::BehaviorContext* behaviorContext = azrtti_cast<AZ::BehaviorContext*>(context))
        {
            behaviorContext->Class<TrackedBySimulationInterfacesComponent>("TrackedBySimulationInterfaces Component Group")
                ->Attribute(AZ::Script::Attributes::Category, "MobileManipulatorDemo Gem Group")
                ;
        }
    }

    void TrackedBySimulationInterfacesComponent::GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided)
    {
        provided.push_back(AZ_CRC_CE("TrackedBySimulationInterfacesComponentService"));
    }

    void TrackedBySimulationInterfacesComponent::GetIncompatibleServices([[maybe_unused]] AZ::ComponentDescriptor::DependencyArrayType& incompatible)
    {
    }

    void TrackedBySimulationInterfacesComponent::GetRequiredServices([[maybe_unused]] AZ::ComponentDescriptor::DependencyArrayType& required)
    {
    }

    void TrackedBySimulationInterfacesComponent::GetDependentServices([[maybe_unused]] AZ::ComponentDescriptor::DependencyArrayType& dependent)
    {
        dependent.push_back(AZ_CRC_CE("SimulationInterfacesService"));
    }
} // namespace MobileManipulatorDemo
