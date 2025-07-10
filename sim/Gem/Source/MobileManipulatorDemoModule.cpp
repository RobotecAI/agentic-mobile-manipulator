
#include <AzCore/Memory/SystemAllocator.h>
#include <AzCore/Module/Module.h>

#include "MobileManipulatorDemoSystemComponent.h"

#include <MobileManipulatorDemo/MobileManipulatorDemoTypeIds.h>

namespace MobileManipulatorDemo
{
    class MobileManipulatorDemoModule
        : public AZ::Module
    {
    public:
        AZ_RTTI(MobileManipulatorDemoModule, MobileManipulatorDemoModuleTypeId, AZ::Module);
        AZ_CLASS_ALLOCATOR(MobileManipulatorDemoModule, AZ::SystemAllocator);

        MobileManipulatorDemoModule()
            : AZ::Module()
        {
            // Push results of [MyComponent]::CreateDescriptor() into m_descriptors here.
            m_descriptors.insert(m_descriptors.end(), {
                MobileManipulatorDemoSystemComponent::CreateDescriptor(),
            });
        }

        /**
         * Add required SystemComponents to the SystemEntity.
         */
        AZ::ComponentTypeList GetRequiredSystemComponents() const override
        {
            return AZ::ComponentTypeList{
                azrtti_typeid<MobileManipulatorDemoSystemComponent>(),
            };
        }
    };
}// namespace MobileManipulatorDemo

#if defined(O3DE_GEM_NAME)
AZ_DECLARE_MODULE_CLASS(AZ_JOIN(Gem_, O3DE_GEM_NAME), MobileManipulatorDemo::MobileManipulatorDemoModule)
#else
AZ_DECLARE_MODULE_CLASS(Gem_MobileManipulatorDemo, MobileManipulatorDemo::MobileManipulatorDemoModule)
#endif
