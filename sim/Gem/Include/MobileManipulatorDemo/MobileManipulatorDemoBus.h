
#pragma once

#include <MobileManipulatorDemo/MobileManipulatorDemoTypeIds.h>

#include <AzCore/EBus/EBus.h>
#include <AzCore/Interface/Interface.h>

namespace MobileManipulatorDemo
{
    class MobileManipulatorDemoRequests
    {
    public:
        AZ_RTTI(MobileManipulatorDemoRequests, MobileManipulatorDemoRequestsTypeId);
        virtual ~MobileManipulatorDemoRequests() = default;
        // Put your public methods here
    };

    class MobileManipulatorDemoBusTraits
        : public AZ::EBusTraits
    {
    public:
        //////////////////////////////////////////////////////////////////////////
        // EBusTraits overrides
        static constexpr AZ::EBusHandlerPolicy HandlerPolicy = AZ::EBusHandlerPolicy::Single;
        static constexpr AZ::EBusAddressPolicy AddressPolicy = AZ::EBusAddressPolicy::Single;
        //////////////////////////////////////////////////////////////////////////
    };

    using MobileManipulatorDemoRequestBus = AZ::EBus<MobileManipulatorDemoRequests, MobileManipulatorDemoBusTraits>;
    using MobileManipulatorDemoInterface = AZ::Interface<MobileManipulatorDemoRequests>;

} // namespace MobileManipulatorDemo
