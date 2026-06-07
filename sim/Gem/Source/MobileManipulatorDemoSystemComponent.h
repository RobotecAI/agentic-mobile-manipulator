
#pragma once

#include <AzCore/Component/Component.h>

#include <MobileManipulatorDemo/MobileManipulatorDemoBus.h>

#include "ROS2/Handlers/IROS2HandlerBase.h"
#include "ROS2/ROS2Bus.h"
#include <AzCore/std/smart_ptr/make_shared.h>

namespace MobileManipulatorDemo
{
    class MobileManipulatorDemoSystemComponent
        : public AZ::Component
        , protected MobileManipulatorDemoRequestBus::Handler
    {
    public:
        AZ_COMPONENT_DECL(MobileManipulatorDemoSystemComponent);

        static void Reflect(AZ::ReflectContext* context);

        static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided);
        static void GetIncompatibleServices(AZ::ComponentDescriptor::DependencyArrayType& incompatible);
        static void GetRequiredServices(AZ::ComponentDescriptor::DependencyArrayType& required);
        static void GetDependentServices(AZ::ComponentDescriptor::DependencyArrayType& dependent);

        MobileManipulatorDemoSystemComponent();
        ~MobileManipulatorDemoSystemComponent();

    protected:
        ////////////////////////////////////////////////////////////////////////
        // MobileManipulatorDemoRequestBus interface implementation

        ////////////////////////////////////////////////////////////////////////

        ////////////////////////////////////////////////////////////////////////
        // AZ::Component interface implementation
        void Init() override;
        void Activate() override;
        void Deactivate() override;
        ////////////////////////////////////////////////////////////////////////

    private:
        AZStd::unordered_map<AZStd::string, AZStd::shared_ptr<ROS2::IROS2HandlerBase>> m_availableRos2Interface;
        template<typename T>
        void RegisterInterface(rclcpp::Node::SharedPtr ros2Node)
        {
            AZStd::shared_ptr handler = AZStd::make_shared<T>();
            handler->Initialize(ros2Node);
            if (handler->IsValid())
            {
                m_availableRos2Interface[handler->GetTypeName()] = AZStd::move(handler);
            }
            handler.reset();
        };
        ROS2::ROS2Requests::NodeChangedEvent::Handler m_nodeHandler;

        void TryRegisterSpawnServiceHandler();
        void DestroyHandlers();
    };
}
