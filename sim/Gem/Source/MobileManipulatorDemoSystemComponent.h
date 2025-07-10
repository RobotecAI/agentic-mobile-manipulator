
#pragma once

#include <AzCore/Component/Component.h>

#include <MobileManipulatorDemo/MobileManipulatorDemoBus.h>

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
    };
}
