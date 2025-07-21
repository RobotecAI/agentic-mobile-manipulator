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
    class WheelAnimToolModule : public WheelAnimToolModuleInterface
    {
    public:
        AZ_RTTI(WheelAnimToolModule, WheelAnimToolModuleTypeId, WheelAnimToolModuleInterface);
        AZ_CLASS_ALLOCATOR(WheelAnimToolModule, AZ::SystemAllocator);
    };
} // namespace WheelAnimTool

#if defined(O3DE_GEM_NAME)
AZ_DECLARE_MODULE_CLASS(AZ_JOIN(Gem_, O3DE_GEM_NAME), WheelAnimTool::WheelAnimToolModule)
#else
AZ_DECLARE_MODULE_CLASS(Gem_WheelAnimTool, WheelAnimTool::WheelAnimToolModule)
#endif
