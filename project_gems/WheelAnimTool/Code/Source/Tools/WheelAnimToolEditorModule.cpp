/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#include <WheelAnimTool/WheelAnimToolTypeIds.h>
#include <WheelAnimToolModuleInterface.h>

namespace WheelAnimTool
{
    class WheelAnimToolEditorModule : public WheelAnimToolModuleInterface
    {
    public:
        AZ_RTTI(WheelAnimToolEditorModule, WheelAnimToolEditorModuleTypeId, WheelAnimToolModuleInterface);
        AZ_CLASS_ALLOCATOR(WheelAnimToolEditorModule, AZ::SystemAllocator);

        WheelAnimToolEditorModule()
        {
            m_descriptors.insert(m_descriptors.end(), {});
        }

        /**
         * Add required SystemComponents to the SystemEntity.
         * Non-SystemComponents should not be added here
         */
        AZ::ComponentTypeList GetRequiredSystemComponents() const override
        {
            return AZ::ComponentTypeList{};
        }
    };
} // namespace WheelAnimTool

#if defined(O3DE_GEM_NAME)
AZ_DECLARE_MODULE_CLASS(AZ_JOIN(Gem_, O3DE_GEM_NAME, _Editor), WheelAnimTool::WheelAnimToolEditorModule)
#else
AZ_DECLARE_MODULE_CLASS(Gem_WheelAnimTool_Editor, WheelAnimTool::WheelAnimToolEditorModule)
#endif
