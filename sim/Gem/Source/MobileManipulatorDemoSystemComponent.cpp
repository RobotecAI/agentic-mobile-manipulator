
#include <AzCore/Serialization/SerializeContext.h>

#include "MobileManipulatorDemoSystemComponent.h"

#include <MobileManipulatorDemo/MobileManipulatorDemoTypeIds.h>

#include <ROS2/ROS2Bus.h>
#include "SpawnEntityServiceHandler.h"

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
        required.push_back(AZ_CRC_CE("ROS2Service"));
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

        auto ros2Node = ROS2::ROS2Interface::Get()->GetNode();
        if (!ros2Node)
        {
            AZ_Trace("MobileManipulatorDemo", "ROS 2 node is not available.");
            return;
        }

        RegisterInterface<SpawnEntityServiceHandler>(ros2Node);
    }

    void MobileManipulatorDemoSystemComponent::Deactivate()
    {
        MobileManipulatorDemoRequestBus::Handler::BusDisconnect();

        for (auto& [handlerType, handler] : m_availableRos2Interface)
        {
            handler.reset();
        }
        m_availableRos2Interface.clear();
    }
}
