
#include <AzCore/Serialization/SerializeContext.h>

#include "MobileManipulatorDemoSystemComponent.h"

#include <MobileManipulatorDemo/MobileManipulatorDemoTypeIds.h>

namespace MobileManipulatorDemo
{
    AZ_COMPONENT_IMPL(MobileManipulatorDemoSystemComponent, "MobileManipulatorDemoSystemComponent",
        MobileManipulatorDemoSystemComponentTypeId);

    void MobileManipulatorDemoSystemComponent::Reflect(AZ::ReflectContext* context)
    {
        if (auto serializeContext = azrtti_cast<AZ::SerializeContext*>(context))
        {
            serializeContext->Class<MobileManipulatorDemoSystemComponent, AZ::Component>()
                ->Version(0)
                ;
        }
    }

    void MobileManipulatorDemoSystemComponent::GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided)
    {
        provided.push_back(AZ_CRC_CE("MobileManipulatorDemoService"));
    }

    void MobileManipulatorDemoSystemComponent::GetIncompatibleServices(AZ::ComponentDescriptor::DependencyArrayType& incompatible)
    {
        incompatible.push_back(AZ_CRC_CE("MobileManipulatorDemoService"));
    }

    void MobileManipulatorDemoSystemComponent::GetRequiredServices([[maybe_unused]] AZ::ComponentDescriptor::DependencyArrayType& required)
    {
    }

    void MobileManipulatorDemoSystemComponent::GetDependentServices([[maybe_unused]] AZ::ComponentDescriptor::DependencyArrayType& dependent)
    {
    }

    MobileManipulatorDemoSystemComponent::MobileManipulatorDemoSystemComponent()
    {
        if (MobileManipulatorDemoInterface::Get() == nullptr)
        {
            MobileManipulatorDemoInterface::Register(this);
        }
    }

    MobileManipulatorDemoSystemComponent::~MobileManipulatorDemoSystemComponent()
    {
        if (MobileManipulatorDemoInterface::Get() == this)
        {
            MobileManipulatorDemoInterface::Unregister(this);
        }
    }

    void MobileManipulatorDemoSystemComponent::Init()
    {
    }

    void MobileManipulatorDemoSystemComponent::Activate()
    {
        MobileManipulatorDemoRequestBus::Handler::BusConnect();
    }

    void MobileManipulatorDemoSystemComponent::Deactivate()
    {
        MobileManipulatorDemoRequestBus::Handler::BusDisconnect();
    }
}
