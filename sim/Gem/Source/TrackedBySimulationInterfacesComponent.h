
#pragma once

#include <AzCore/Component/Component.h>
#include <MobileManipulatorDemo/TrackedBySimulationInterfacesInterface.h>
#include <SimulationInterfaces/Result.h>
#include <AzCore/Component/TickBus.h>

namespace MobileManipulatorDemo
{
    /*
    * This component will register its entity in the simulation interfaces
    * while preserving the naming convention from the older version of that gem ("{ParentName}_{ChildName}")
    * to be compatible with scripts that used the older version.
    */

    class TrackedBySimulationInterfacesComponent
        : public AZ::Component
        , public AZ::TickBus::Handler
        , public TrackedBySimulationInterfacesRequestBus::Handler
    {
    public:
        AZ_COMPONENT_DECL(TrackedBySimulationInterfacesComponent);

        static void Reflect(AZ::ReflectContext* context);

        static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided);
        static void GetIncompatibleServices(AZ::ComponentDescriptor::DependencyArrayType& incompatible);
        static void GetRequiredServices(AZ::ComponentDescriptor::DependencyArrayType& required);
        static void GetDependentServices(AZ::ComponentDescriptor::DependencyArrayType& dependent);

    protected:
        void Activate() override;
        void Deactivate() override;

        void OnTick(float deltaTime, AZ::ScriptTimePoint time) override;

        AZ::Outcome<AZStd::string, SimulationInterfaces::FailedResult> m_registeredName;
    };
} // namespace MobileManipulatorDemo
