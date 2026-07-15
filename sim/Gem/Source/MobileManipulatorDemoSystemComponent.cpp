
#include <AzCore/Serialization/SerializeContext.h>

#include "MobileManipulatorDemoSystemComponent.h"

#include <MobileManipulatorDemo/MobileManipulatorDemoTypeIds.h>

#include <ROS2/ROS2Bus.h>
#include "SpawnEntityServiceHandler.h"
#include "SpawnEntitiesServiceHandler.h"

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
        : m_nodeHandler([this] (std::shared_ptr<rclcpp::Node> node)
            {
                if (node)
                {
                    TryRegisterSpawnServiceHandler();
                }
                else
                {
                    DestroyHandlers();
                }
            })
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

    void MobileManipulatorDemoSystemComponent::TryRegisterSpawnServiceHandler()
    {
        auto ros2Node = ROS2::ROS2Interface::Get()->GetNode();
        if (!ros2Node)
        {
            return;
        }

        RegisterInterface<SpawnEntityServiceHandler>(ros2Node);
        RegisterInterface<SpawnEntitiesServiceHandler>(ros2Node);
    }

    void MobileManipulatorDemoSystemComponent::DestroyHandlers()
    {
        for (auto& [handlerType, handler] : m_availableRos2Interface)
        {
            handler.reset();
        }
        m_availableRos2Interface.clear();
    }

    void MobileManipulatorDemoSystemComponent::Activate()
    {
        MobileManipulatorDemoRequestBus::Handler::BusConnect();

        ROS2::ROS2Interface::Get()->ConnectOnNodeChanged(m_nodeHandler);
        TryRegisterSpawnServiceHandler();
    }

    void MobileManipulatorDemoSystemComponent::Deactivate()
    {
        MobileManipulatorDemoRequestBus::Handler::BusDisconnect();

        m_nodeHandler.Disconnect();
        DestroyHandlers();
    }
}
