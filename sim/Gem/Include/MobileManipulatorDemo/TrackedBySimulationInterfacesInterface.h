
#pragma once

#include <AzCore/Component/ComponentBus.h>

namespace MobileManipulatorDemo
{
    class TrackedBySimulationInterfacesRequests
        : public AZ::ComponentBus
    {
    public:
        AZ_RTTI(MobileManipulatorDemo::TrackedBySimulationInterfacesRequests, "{F3A61246-DBEB-4A8E-B356-98171996A7E3}");

        // Put your public request methods here.
        
        // Put notification events here. Examples:
        // void RegisterEvent(AZ::EventHandler<...> notifyHandler);
        // AZ::Event<...> m_notifyEvent1;
        
    };

    using TrackedBySimulationInterfacesRequestBus = AZ::EBus<TrackedBySimulationInterfacesRequests>;

} // namespace MobileManipulatorDemo
