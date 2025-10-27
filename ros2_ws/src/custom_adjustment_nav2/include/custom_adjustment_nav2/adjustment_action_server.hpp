// Copyright (C) 2025 Advanced Micro Devices, Inc.
// Developed by Robotec.ai sp. z o.o.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//         http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef CUSTOM_ADJUSTMENT__ADJUSTMENT_ACTION_SERVER_HPP_
#define CUSTOM_ADJUSTMENT__ADJUSTMENT_ACTION_SERVER_HPP_

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

#include "custom_adjustment_nav2/action/adjust.hpp"

namespace custom_adjustment
{

class AdjustmentActionServer : public rclcpp::Node
{
public:
  using Adjust = custom_adjustment_nav2::action::Adjust;
  using GoalHandleAdjust = rclcpp_action::ServerGoalHandle<Adjust>;

  explicit AdjustmentActionServer(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
  ~AdjustmentActionServer() = default;

private:
  // Action server callbacks
  rclcpp_action::GoalResponse handle_goal(
    const rclcpp_action::GoalUUID & uuid,
    std::shared_ptr<const Adjust::Goal> goal);

  rclcpp_action::CancelResponse handle_cancel(
    const std::shared_ptr<GoalHandleAdjust> goal_handle);

  void handle_accepted(const std::shared_ptr<GoalHandleAdjust> goal_handle);

  void execute(const std::shared_ptr<GoalHandleAdjust> goal_handle);

  // Helper methods
  geometry_msgs::msg::PoseStamped getCurrentPose();
  double calculateDistance(
    const geometry_msgs::msg::PoseStamped & current,
    const geometry_msgs::msg::PoseStamped & target);
  double calculateAngleDifference(
    const geometry_msgs::msg::PoseStamped & current,
    const geometry_msgs::msg::PoseStamped & target);

  // ROS2 interfaces
  rclcpp_action::Server<Adjust>::SharedPtr action_server_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;


  // TF2
  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;

  // Parameters
  std::string robot_base_frame_;
  std::string global_frame_;
  std::string control_topic_;
  double control_frequency_;
  double timeout_;  // seconds

  // P-controller parameters
  double linear_kp_;
  double angular_kp_;
  double max_linear_speed_;    // m/s
  double max_angular_speed_;   // rad/s
  double max_angular_error_to_stop_linear_; // rad
};

}  // namespace custom_adjustment

#endif  // CUSTOM_ADJUSTMENT__ADJUSTMENT_ACTION_SERVER_HPP_
