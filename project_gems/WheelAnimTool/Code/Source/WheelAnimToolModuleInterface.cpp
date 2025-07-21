/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#include "WheelAnimToolModuleInterface.h"
#include <AzCore/Memory/Memory.h>

#include "Clients/WheelAnimComponent.h"
#include <WheelAnimTool/WheelAnimToolTypeIds.h>

namespace WheelAnimTool
{
    AZ_TYPE_INFO_WITH_NAME_IMPL(WheelAnimToolModuleInterface, "WheelAnimToolModuleInterface", WheelAnimToolModuleInterfaceTypeId);

    AZ_RTTI_NO_TYPE_INFO_IMPL(WheelAnimToolModuleInterface, AZ::Module);

    AZ_CLASS_ALLOCATOR_IMPL(WheelAnimToolModuleInterface, AZ::SystemAllocator);

    WheelAnimToolModuleInterface::WheelAnimToolModuleInterface()
    {
        // Push results of [MyComponent]::CreateDescriptor() into m_descriptors here.
        // Add ALL components descriptors associated with this gem to m_descriptors.
        // This will associate the AzTypeInfo information for the components with the the SerializeContext, BehaviorContext and EditContext.
        // This happens through the [MyComponent]::Reflect() function.
        m_descriptors.insert(m_descriptors.end(), { WheelAnimComponent::CreateDescriptor() });
    }

    AZ::ComponentTypeList WheelAnimToolModuleInterface::GetRequiredSystemComponents() const
    {
        return AZ::ComponentTypeList{

        };
    }
} // namespace WheelAnimTool
