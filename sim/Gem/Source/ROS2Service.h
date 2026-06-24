// NOTE: This file is a slightly modified copy of ROS2/Code/Include/ROS2/Handlers/ROS2ServiceBase.h

/*
* Copyright (c) Contributors to the Open 3D Engine Project.
* For complete copyright and license terms please see the LICENSE at the root of this distribution.
*
* SPDX-License-Identifier: Apache-2.0 OR MIT
*
*/

#pragma once

#include <ROS2/Handlers/IROS2HandlerBase.h>
#include <AzCore/std/containers/unordered_set.h>
#include <AzCore/std/optional.h>
#include <rclcpp/service.hpp>

namespace MobileManipulatorDemo
{
    template<typename RosServiceType>
    class ROS2Service : public virtual ROS2::IROS2HandlerBase
    {
    public:
        using Request = typename RosServiceType::Request;
        using Response = typename RosServiceType::Response;
        using ServiceHandle = std::shared_ptr<rclcpp::Service<RosServiceType>>;
        virtual ~ROS2Service() = default;

        void Initialize(rclcpp::Node::SharedPtr& node) override
        {
            CreateService(node);
        }

        void SendResponse(Response response)
        {
            AZ_Assert(m_serviceHandle, "Failed to get m_serviceHandle");
            AZ_Assert(m_lastRequestHeader, "Failed to get last request header ptr");
            m_serviceHandle->send_response(*m_lastRequestHeader, response);
        }

        bool IsValid() const override
        {
            return m_serviceHandle != nullptr;
        }

    protected:
        //! This function is called when a service request is received.
        virtual AZStd::optional<Response> HandleServiceRequest(const std::shared_ptr<rmw_request_id_t> header, const Request& request) = 0;

    private:
        void CreateService(rclcpp::Node::SharedPtr& node)
        {
            auto serviceName = GetDefaultName();
            const std::string serviceNameStr(serviceName.data(), serviceName.size());
            m_serviceHandle = node->create_service<RosServiceType>(
                serviceNameStr,
                [this](
                    const ServiceHandle service_handle,
                    const std::shared_ptr<rmw_request_id_t> header,
                    const std::shared_ptr<Request> request)
                {
                    m_lastRequestHeader = header;
                    auto response = HandleServiceRequest(header, *request);
                    // if no response passed it means, that handleServiceRequest will send response in defined callback after time consuming
                    // task, header needs to be cached
                    if (response.has_value())
                    {
                        service_handle->send_response(*header, response.value());
                    }
                });
        }

        std::shared_ptr<rmw_request_id_t> m_lastRequestHeader = nullptr;
        ServiceHandle m_serviceHandle;
    };

} // namespace MobileManipulatorDemo
