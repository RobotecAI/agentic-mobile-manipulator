/*
* Copyright (c) Contributors to the Open 3D Engine Project.
 * For complete copyright and license terms please see the LICENSE at the root of this distribution.
 *
 * SPDX-License-Identifier: Apache-2.0 OR MIT
 *
 */

#include "WheelAnimComponent.h"

#include <Atom/RPI.Public/AuxGeom/AuxGeomFeatureProcessorInterface.h>
#include <Atom/RPI.Public/Scene.h>
#include <AzCore/Component/TransformBus.h>
#include <AzCore/Serialization/EditContext.h>
#include <AzCore/Serialization/SerializeContext.h>
#include <AzFramework/Physics/Common/PhysicsSimulatedBody.h>
#include <AzFramework/Physics/Components/SimulatedBodyComponentBus.h>
#include <AzFramework/Physics/PhysicsScene.h>
#include <AzFramework/Physics/RigidBodyBus.h>
#include <AzFramework/Physics/SimulatedBodies/RigidBody.h>
#include <Eigen/Dense>
namespace WheelAnimTool
{
    namespace EigenO3DE
    {
        Eigen::Vector2d ToEigen(const AZ::Vector2& vec)
        {
            return Eigen::Vector2d(vec.GetX(), vec.GetY());
        }
        Eigen::Vector3d ToEigen(const AZ::Vector3& vec)
        {
            return Eigen::Vector3d(vec.GetX(), vec.GetY(), vec.GetZ());
        }

        AZ::Vector3 ToO3DE(const Eigen::Vector3d& vec)
        {
            return AZ::Vector3(vec.x(), vec.y(), vec.z());
        }
    } // namespace EigenO3DE

    namespace DebugDraw
    {
        void DrawSphere(
            AZ::RPI::AuxGeomDrawPtr queue,
            const AZ::Transform& frame,
            const AZ::Color& color,
            float radius,
            const AZ::Vector3& loc = AZ::Vector3::CreateZero())
        {
            if (!queue)
            {
                return;
            }

            queue->DrawSphere(
                frame.TransformPoint(loc),
                AZ::Vector3::CreateAxisZ(),
                radius,
                color,
                AZ::RPI::AuxGeomDraw::DrawStyle::Line,
                AZ::RPI::AuxGeomDraw::DepthTest::Off);
        }

        void DrawVector(AZ::RPI::AuxGeomDrawPtr queue, const AZ::Transform& frame, const AZ::Color& color, const AZ::Vector3& vector)
        {
            if (!queue)
            {
                return;
            }
            AZStd::vector<AZ::Vector3> linePoints;
            AZStd::vector<AZ::Color> colors;
            colors.push_back(color);
            colors.push_back(color);

            linePoints.push_back(frame.GetTranslation());
            linePoints.push_back(frame.GetTranslation() + frame.GetRotation().TransformVector(vector));

            AZ::RPI::AuxGeomDraw::AuxGeomDynamicDrawArguments drawArgs;
            drawArgs.m_colors = colors.data();
            drawArgs.m_verts = linePoints.data();
            drawArgs.m_depthTest = AZ::RPI::AuxGeomDraw::DepthTest::Off;
            drawArgs.m_colorCount = colors.size();
            drawArgs.m_vertCount = linePoints.size();
            queue->DrawLines(drawArgs);
        }
    } // namespace DebugDraw
    void WheelAnimComponent::Reflect(AZ::ReflectContext* context)
    {
        if (AZ::SerializeContext* serialize = azrtti_cast<AZ::SerializeContext*>(context))
        {
            serialize->Class<WheelAnimComponent, AZ::Component>()
                ->Version(0)
                ->Field("AnimationType", &WheelAnimComponent::m_animationType)
                ->Field("WheelEntities", &WheelAnimComponent::m_wheelEntities)
                ->Field("RollerDirections", &WheelAnimComponent::m_rollerDirections)
                ->Field("WheelRadius", &WheelAnimComponent::m_wheelRadius)
                ->Field("DebugDraw", &WheelAnimComponent::m_debugDraw)
                ->Field("WheelAxis", &WheelAnimComponent::m_wheelAxis);

            if (AZ::EditContext* ec = serialize->GetEditContext())
            {
                ec->Class<WheelAnimComponent>("Wheel Animation", "Component for animating for robots wheels")
                    ->ClassElement(AZ::Edit::ClassElements::EditorData, "")
                    ->Attribute(AZ::Edit::Attributes::Category, "Robotics")
                    ->Attribute(AZ::Edit::Attributes::AppearsInAddComponentMenu, AZ_CRC("Game"))
                    ->DataElement(
                        AZ::Edit::UIHandlers::ComboBox,
                        &WheelAnimComponent::m_animationType,
                        "Animation Type",
                        "Type of wheel animation to use.")
                    ->EnumAttribute(AnimationType::Mecanum, "Mecanum")
                    ->EnumAttribute(AnimationType::Differential, "Differential")
                    ->Attribute(AZ::Edit::Attributes::ChangeNotify, AZ::Edit::PropertyRefreshLevels::EntireTree)
                    ->DataElement(
                        AZ::Edit::UIHandlers::Default,
                        &WheelAnimComponent::m_wheelEntities,
                        "Wheel Entities",
                        "List of wheel entities to animate")
                    ->DataElement(
                        AZ::Edit::UIHandlers::Default,
                        &WheelAnimComponent::m_rollerDirections,
                        "Roller Directions",
                        "List of roller directions for each wheel. Each direction is a 2D vector representing the direction of the rollers "
                        "on the wheel.")
                    ->Attribute(AZ::Edit::Attributes::Visibility, &WheelAnimComponent::RollerDirectionVisible)
                    ->DataElement(
                        AZ::Edit::UIHandlers::Default,
                        &WheelAnimComponent::m_wheelRadius,
                        "Wheel Radius",
                        "Radius of the wheels. This is used for visualizing the wheels in the scene.")
                    ->DataElement(
                        AZ::Edit::UIHandlers::Default,
                        &WheelAnimComponent::m_wheelAxis,
                        "Wheel Axis",
                        "Axis of rotation for the wheels. This is used to determine the direction of rotation.")
                    ->DataElement(
                        AZ::Edit::UIHandlers::Default,
                        &WheelAnimComponent::m_debugDraw,
                        "Debug Draw",
                        "Enable or disable debug drawing of wheel animations.");
            }
        }
    }

    void WheelAnimComponent::Activate()
    {
        m_wheelAxis.NormalizeSafe();
        if (m_animationType == AnimationType::Mecanum)
        {
            AZ_Printf("WheelAnimComponent", "Using Mecanum wheel animation type");
            AZ_Error(
                "WheelAnimComponent",
                m_wheelEntities.size() == m_rollerDirections.size(),
                "The same number of wheel entities and roller directions is expected for Mecanum animation type");
            if (m_wheelEntities.size() != m_rollerDirections.size())
            {
                return;
            }
        }
        else if (m_animationType == AnimationType::Differential)
        {
            AZ_Printf("WheelAnimComponent", "Using Differential wheel animation type");
            m_rollerDirections.clear(); // No roller directions needed for differential drive
            m_rollerDirections.resize(m_wheelEntities.size(), AZ::Vector2::CreateZero()); // Initialize with zero vectors
        }

        if (m_debugDraw)
        {
            auto* entityScene = AZ::RPI::Scene::GetSceneForEntityId(GetEntityId());
            m_drawQueue = AZ::RPI::AuxGeomFeatureProcessorInterface::GetDrawQueueForScene(entityScene);
        }

        AZ::TickBus::Handler::BusConnect();
    }

    void WheelAnimComponent::Deactivate()
    {
        AZ::TickBus::Handler::BusDisconnect();
        m_jacobian = Eigen::MatrixXd();
    }

    //! \brief Create a row of the Jacobian matrix for a mecanum wheel.
    //! \param rollerDirection The direction of the rollers on the wheel, normalized.
    //! \param wheelPosition The position of the wheel in 3D space.
    Eigen::Vector3d CreateMecanumJacobianRow(Eigen::Vector2d rollerDirection, const Eigen::Vector3d& wheelPosition)
    {
        // Normalize roller direction
        rollerDirection.normalize();

        // I've tried to recreate the jacobian row based on the roller direction and wheel position.
        // The model is based on equation 29 from paper :
        //    "Development of the Laboratory Work: Modeling of a Mobile Robot on Mecanum Wheels Kinematics" by
        //     Daniil S. Alhanov and Vasily I. Rubtsov
        // The model is like this:
        // \omega_1 = \frac{1}{r} (v_x - v_y - \frac{L_x+L_y}{2} * \omega)
        // \omega_2 = \frac{1}{r} (v_x + v_y + \frac{L_x+L_y}{2} * \omega)
        // \omega_3 = \frac{1}{r} (v_x + v_y - \frac{L_x+L_y}{2} * \omega)
        // \omega_4 = \frac{1}{r} (v_x - v_y + \frac{L_x+L_y}{2} * \omega)
        // where
        //  - \omega_i is the angular velocity of the i-th wheel,
        //  - v_x and v_y are the linear velocities of the robot,
        //  - \omega is the angular velocity of the robot, r is the wheel radius,
        //  - L_x is robot track and L_y is robot wheelbase.

        const float Lx = abs(wheelPosition.x()) * 2.f; // Assuming wheelPosition.x() is the half of track width
        const float Ly = abs(wheelPosition.y()) * 2.f; // Assuming wheelPosition.y() is the half of wheelbase
        const float sign = (wheelPosition.y() > 0.f) ? -1.f : 1.f; // Sign based if robot wheel is on the left or right side

        // Create jacobian row
        Eigen::Vector3d jacobianRow;
        jacobianRow << rollerDirection.x(), rollerDirection.y(), sign * (Lx + Ly) / 2.f;
        return jacobianRow;
    }

    Eigen::Vector3d CreateDifferentialJacobianRow(const Eigen::Vector3d& wheelPosition)
    {
        // For differential drive, the model for wheel speed is simpler:
        // \omega_1 = \frac{1}{r} (v_x + \frac{L_x}{2} * \omega)
        // \omega_2 = \frac{1}{r} (v_x - \frac{L_x}{2} * \omega)
        // where
        //  - \omega_i is the angular velocity of the i-th wheel,
        //  - v_x is the linear velocity of the robot,
        //  - \omega is the angular velocity of the robot, r is the wheel radius,
        //  - L_x is robot track.

        const float Lx = abs(wheelPosition.x()) * 2.f; // Assuming wheelPosition.x() is the half of track width
        const float sign = (wheelPosition.y() > 0.f) ? -1.f : 1.f; // Sign based if robot wheel is on the left or right side

        Eigen::Vector3d jacobianRow;
        jacobianRow << 1.0, 0.0, sign * (Lx / 2.f); // we assume the robot X axis is forward, Y axis is left, and Z axis is up
        return jacobianRow;
    }

    bool WheelAnimComponent::InitJacobian()
    {
        AZ_Assert(
            m_wheelEntities.size() == m_rollerDirections.size(), "The same number of wheel entities and roller directions is expected");
        const uint numWheels = static_cast<uint>(m_wheelEntities.size());
        AZ_Assert(numWheels > 0, "At least one wheel entity is expected");
        if ( m_wheelEntities.size() != m_rollerDirections.size()  || m_wheelEntities.empty())
        {
            return false;
        }
        // compute geometrical center of the wheels
        Eigen::Vector3d meanWheelPosition = Eigen::Vector3d::Zero();
        Eigen::Matrix<double, Eigen::Dynamic, 3> wheelPositions(numWheels, 3);

        AZ_Assert(GetEntity()->GetTransform(), "No transform interface");
        const AZ::Transform worldTransform = GetEntity()->GetTransform()->GetWorldTM();
        const AZ::Transform worldTransformInv = worldTransform.GetInverse();
        for (int i = 0; i < numWheels; ++i)
        {
            const AZ::EntityId wheelEntity = m_wheelEntities[i];
            AZ::Vector3 wheelPos = AZ::Vector3::CreateZero();
            AZ::TransformBus::EventResult(wheelPos, wheelEntity, &AZ::TransformInterface::GetWorldTranslation);
            // transform wheel position to local space
            const AZ::Vector3 wheelPosLoc = worldTransformInv.TransformPoint(wheelPos);
            meanWheelPosition += EigenO3DE::ToEigen(wheelPosLoc);
            wheelPositions.row(i) = EigenO3DE::ToEigen(wheelPosLoc);
        }

        for (int i = 0; i < numWheels; ++i)
        {
            const AZ::EntityId wheelEntity = m_wheelEntities[i];
            AZ::Vector3 wheelPos = AZ::Vector3::CreateZero();
            AZ::TransformBus::EventResult(wheelPos, wheelEntity, &AZ::TransformInterface::GetWorldTranslation);
            // transform wheel position to local space
            const AZ::Vector3 wheelPosLoc = worldTransformInv.TransformPoint(wheelPos);
            meanWheelPosition += EigenO3DE::ToEigen(wheelPosLoc);
            wheelPositions.row(i) = EigenO3DE::ToEigen(wheelPosLoc);
        }
        meanWheelPosition /= numWheels;

        // calculate location w.r.t the mean wheel position
        for (int i = 0; i < numWheels; ++i)
        {
            wheelPositions.row(i) -= meanWheelPosition;
        }

        if (m_jacobian.rows() != numWheels)
        {
            // update jacobian matrix size
            m_jacobian = Eigen::MatrixXd(numWheels, 3); // we transform 3D speed to 1D speed of wheel
            for (int i = 0; i < numWheels; ++i)
            {
                const Eigen::Vector3d wheelPosition = wheelPositions.row(i);
                if (m_animationType == AnimationType::Mecanum)
                {
                    const Eigen::Vector2d rollerDirection = EigenO3DE::ToEigen(m_rollerDirections[i]);
                    m_jacobian.row(i) = CreateMecanumJacobianRow(rollerDirection, wheelPosition);
                }
                else if (m_animationType == AnimationType::Differential)
                {
                    m_jacobian.row(i) = CreateDifferentialJacobianRow(wheelPosition);
                }
                else
                {
                    AZ_Error("WheelAnimComponent", false, "Unknown animation type");
                    m_jacobian.row(i) = Eigen::Vector3d::Zero();
                }
            }
        }
        return true;
    }

    void WheelAnimComponent::OnTick(float deltaTime, AZ::ScriptTimePoint time)
    {
        if (m_jacobian.size() == 0)
        {
            if (!InitJacobian())
            {
                // if we failed to compute Jacobian matrix, we disconnected
                AZ::TickBus::Handler::BusDisconnect();
                return;
            }

        }
        AzPhysics::RigidBody* rigidBody = nullptr;
        Physics::RigidBodyRequestBus::EventResult(rigidBody, GetEntityId(), &Physics::RigidBodyRequests::GetRigidBody);
        AZ_Error("WheelAnimComponent", rigidBody, "Rigid body not found for entity %s", GetEntityId().ToString().c_str());

        const AZ::Transform worldTransform = GetEntity()->GetTransform()->GetWorldTM();
        const AZ::Transform worldTransformInv = worldTransform.GetInverse();

        const auto linearVelocityLoc = worldTransformInv.TransformVector(rigidBody->GetLinearVelocity());
        const auto angularVelocityLoc = worldTransformInv.TransformVector(rigidBody->GetAngularVelocity());
        if (m_debugDraw)
        {
            using namespace DebugDraw;
            DrawSphere(m_drawQueue, worldTransform, AZ::Colors::Blue, 0.1);
            DrawVector(m_drawQueue, GetEntity()->GetTransform()->GetWorldTM(), AZ::Colors::Red, linearVelocityLoc);
            DrawVector(m_drawQueue, GetEntity()->GetTransform()->GetWorldTM(), AZ::Colors::Green, angularVelocityLoc);
        }

        Eigen::Vector3d robotState;
        robotState << linearVelocityLoc.GetX(), linearVelocityLoc.GetY(), angularVelocityLoc.GetZ();
        Eigen::VectorXd wheelSpeeds = m_jacobian * robotState;

        for (int i = 0; i < wheelSpeeds.size(); ++i)
        {
            const float wheelSpeed = static_cast<float>(wheelSpeeds(i));

            AZ::Transform wheelTransform = AZ::Transform::CreateIdentity();
            AZ::TransformBus::EventResult(wheelTransform, m_wheelEntities[i], &AZ::TransformInterface::GetWorldTM);

            const float wheelAngle = (wheelSpeed / m_wheelRadius) * deltaTime; // angle in radians
            const AZ::Quaternion wheelRotationIncrement = AZ::Quaternion::CreateFromAxisAngle(m_wheelAxis, wheelAngle);
            const AZ::Quaternion newWheelRotation = wheelTransform.GetRotation() * wheelRotationIncrement;

            AZ::TransformBus::Event(m_wheelEntities[i], &AZ::TransformInterface::SetWorldRotationQuaternion, newWheelRotation);
            if (m_debugDraw)
            {
                using namespace DebugDraw;
                DrawSphere(m_drawQueue, wheelTransform, AZ::Colors::Yellow, 0.0125);
                AZ::Vector3 wheelSpeedVec = wheelSpeed * m_wheelAxis;
                DrawVector(m_drawQueue, wheelTransform, AZ::Colors::Red, wheelSpeedVec);
            }
        }
    }
    AZ::Crc32 WheelAnimComponent::RollerDirectionVisible() const
    {
        return m_animationType == AnimationType::Mecanum ? AZ::Edit::PropertyVisibility::Show : AZ::Edit::PropertyVisibility::Hide;
    }
} // namespace WheelAnimTool
