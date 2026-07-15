// NOTE: this file is a slightly modified copy of SimulationInterfaces/Code/Source/Services/SpawnServiceUtils.h

/*
 * Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#pragma once

#include <AzCore/Math/Transform.h>
#include <AzCore/Outcome/Outcome.h>
#include <AzCore/std/string/string.h>
#include <AzCore/std/string/string_view.h>
#include <AzCore/Component/EntityId.h>
#include <AzCore/std/containers/vector.h>

namespace MobileManipulatorDemo::SpawnServiceUtils
{
    bool ValidateEntityName(AZStd::string_view entityName);
    bool ValidateNamespaceName(AZStd::string_view namespaceName);

    //! Validates that the transform has a normalised rotation quaternion and a finite, in-range translation.
    //! @param transform     Transform to validate.
    //! @param quaternionTolerance  Tolerance on |quaternion| - 1.0f. Defaults to 1e-3f.
    //! @param maxTranslation Maximum allowed absolute value per axis in metres. Defaults to 1e7f (~10 000 km).
    //! @return Success when valid, Failure with a descriptive error message when not.
    AZ::Outcome<void, AZStd::string> ValidateTransformNormalized(
        const AZ::Transform& transform, float quaternionTolerance = 1e-3f, float maxTranslation = 1e7f);

    AZStd::vector<AZ::EntityId> GetAllDescendants(AZ::EntityId parent);
    AZStd::string GetEntityName(AZ::EntityId entityId);
    void RegisterChildGrippingPoints(const AZStd::string& rootName);
} // namespace MobileManipulatorDemo::SpawnServiceUtils
