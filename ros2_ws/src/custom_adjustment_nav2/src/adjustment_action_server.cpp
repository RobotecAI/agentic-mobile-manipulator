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

#include "custom_adjustment_nav2/adjustment_action_server.hpp"
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/utils.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <cmath>

namespace custom_adjustment
{

AdjustmentActionServer::AdjustmentActionServer(const rclcpp::NodeOptions & options)
: Node("adjustment_action_server", options)
{
  RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Initializing adjustment action server");

  // Declare and get parameters
  this->declare_parameter("robot_base_frame", "base_link");
  this->declare_parameter("global_frame", "map");
  this->declare_parameter("control_topic", "cmd_vel");
  this->declare_parameter("control_frequency", 20.0);
  this->declare_parameter("timeout", 10.0);
  this->declare_parameter("linear_kp", 0.5);
  this->declare_parameter("angular_kp", 1.0);
  this->declare_parameter("max_linear_speed", 0.2);
  this->declare_parameter("max_angular_speed", 0.5);
  this->declare_parameter("max_angular_error_to_stop_linear", 0.2);

  robot_base_frame_ = this->get_parameter("robot_base_frame").as_string();
  global_frame_ = this->get_parameter("global_frame").as_string();
  control_frequency_ = this->get_parameter("control_frequency").as_double();
  control_topic_ = this->get_parameter("control_topic").as_string();
  timeout_ = this->get_parameter("timeout").as_double();
  linear_kp_ = this->get_parameter("linear_kp").as_double();
  angular_kp_ = this->get_parameter("angular_kp").as_double();
  max_linear_speed_ = this->get_parameter("max_linear_speed").as_double();
  max_angular_speed_ = this->get_parameter("max_angular_speed").as_double();
  max_angular_error_to_stop_linear_ = this->get_parameter("max_angular_error_to_stop_linear").as_double();

  RCLCPP_INFO(
    get_logger(),
    "AdjustmentActionServer: Using frames - base: %s, global: %s, freq: %.1f Hz, topic: %s, timeout: %.1f s",
    robot_base_frame_.c_str(), global_frame_.c_str(), control_frequency_, control_topic_.c_str(), timeout_);

  RCLCPP_INFO(
    get_logger(),
    "AdjustmentActionServer: Controller gains - linear_kp: %.2f, angular_kp: %.2f",
    linear_kp_, angular_kp_);

  RCLCPP_INFO(
    get_logger(),
    "AdjustmentActionServer: Speed limits - max_linear: %.2f m/s, max_angular: %.2f rad/s, max_angular_error_for_linear: %.2f rad",
    max_linear_speed_, max_angular_speed_, max_angular_error_to_stop_linear_);


  // Initialize TF2
  tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  // Create velocity publisher
  cmd_vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>(control_topic_, 10);

  // Create action server
  action_server_ = rclcpp_action::create_server<Adjust>(
    this,
    "adjust",
    std::bind(&AdjustmentActionServer::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
    std::bind(&AdjustmentActionServer::handle_cancel, this, std::placeholders::_1),
    std::bind(&AdjustmentActionServer::handle_accepted, this, std::placeholders::_1));

  RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Action server 'adjust' is ready!");
}

rclcpp_action::GoalResponse AdjustmentActionServer::handle_goal(
  const rclcpp_action::GoalUUID & uuid,
  std::shared_ptr<const Adjust::Goal> goal)
{
  (void)uuid;
  RCLCPP_INFO(
    get_logger(),
    "AdjustmentActionServer: Received adjustment goal request - target: (%.2f, %.2f), tolerances: pos=%.3f, ori=%.3f",
    goal->target_pose.pose.position.x,
    goal->target_pose.pose.position.y,
    goal->position_tolerance,
    goal->orientation_tolerance);

  return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
}

rclcpp_action::CancelResponse AdjustmentActionServer::handle_cancel(
  const std::shared_ptr<GoalHandleAdjust> goal_handle)
{
  (void)goal_handle;
  RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Received request to cancel adjustment goal");
  return rclcpp_action::CancelResponse::ACCEPT;
}

void AdjustmentActionServer::handle_accepted(const std::shared_ptr<GoalHandleAdjust> goal_handle)
{
  RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Goal accepted, starting execution");
  // Execute in a new thread to avoid blocking
  std::thread{std::bind(&AdjustmentActionServer::execute, this, std::placeholders::_1), goal_handle}.detach();
}

void AdjustmentActionServer::execute(const std::shared_ptr<GoalHandleAdjust> goal_handle)
{
  RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Starting adjustment execution");

  const auto goal = goal_handle->get_goal();
  auto feedback = std::make_shared<Adjust::Feedback>();
  auto result = std::make_shared<Adjust::Result>();

  rclcpp::Rate loop_rate(control_frequency_);

  // Start timeout tracking
  const auto start_time = this->now();
  const auto timeout_duration = rclcpp::Duration::from_seconds(timeout_);

  // Main control loop
  while (rclcpp::ok()) {
    // Check if goal is canceling
    if (goal_handle->is_canceling()) {
      RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Goal canceled");
      result->success = false;
      result->message = "Goal was canceled";
      goal_handle->canceled(result);
      for (int i = 0; i < 5; i++)
      {
        cmd_vel_pub_->publish(geometry_msgs::msg::Twist()); // stop robot
      }
      return;
    }

    // Check timeout
    const auto elapsed = this->now() - start_time;
    if (elapsed > timeout_duration) {
      RCLCPP_WARN(get_logger(), "AdjustmentActionServer: Timeout reached (%.2f seconds)", timeout_);
      result->success = false;
      result->message = "Timeout: Adjustment could not be completed in time";
      goal_handle->abort(result);
      for (int i = 0; i < 5; i++)
      {
        cmd_vel_pub_->publish(geometry_msgs::msg::Twist()); // stop robot
      }
      return;
    }

    // Get current pose
    try {
      feedback->current_pose = getCurrentPose();
    } catch (const std::exception & e) {
      RCLCPP_ERROR(get_logger(), "AdjustmentActionServer: Failed to get current pose: %s", e.what());
      result->success = false;
      result->message = std::string("Failed to get current pose: ") + e.what();
      goal_handle->abort(result);
      for (int i =0; i < 5; i++)
      {
        cmd_vel_pub_->publish(geometry_msgs::msg::Twist()); // stop robot
      }
      return;
    }

    // Calculate remaining distance and angle
    feedback->distance_remaining = calculateDistance(feedback->current_pose, goal->target_pose);
    feedback->angle_remaining = calculateAngleDifference(feedback->current_pose, goal->target_pose);

    // Calculate progress
    feedback->progress_percentage = 50.0f; // Placeholder

    RCLCPP_INFO_THROTTLE(
      get_logger(), *get_clock(), 1000,
      "AdjustmentActionServer: Distance remaining: %.3f m, Angle remaining: %.3f rad",
      feedback->distance_remaining,
      feedback->angle_remaining);

    // Publish feedback
    goal_handle->publish_feedback(feedback);

    // Check if goal is reached
    if (feedback->distance_remaining < goal->position_tolerance &&
        std::abs(feedback->angle_remaining) < goal->orientation_tolerance)
    {
      RCLCPP_INFO(get_logger(), "AdjustmentActionServer: Goal reached!");
      result->success = true;
      result->message = "Adjustment completed successfully";
      result->final_pose = feedback->current_pose;
      goal_handle->succeed(result);
      for (int i =0; i < 5; i++)
      {
        cmd_vel_pub_->publish(geometry_msgs::msg::Twist()); // stop robot
      }
      return;
    }


    const auto goal_pose = goal->target_pose;
    const auto current_pose = feedback->current_pose;
    geometry_msgs::msg::Twist cmd_vel;

    // Simple proportional controller - angular
    const double angular_error = calculateAngleDifference(current_pose, goal_pose);
    const double angular_speed = std::clamp(angular_kp_ * angular_error, -max_angular_speed_, max_angular_speed_);
    cmd_vel.angular.z = angular_speed;

    if (std::abs(angular_error) < max_angular_error_to_stop_linear_) // allow linear movement only if angular error is small
    {
      // Simple proportional controller - linear
      geometry_msgs::msg::Point goal_position = goal_pose.pose.position;

      // transform goal position to robot frame - use tf2
      tf2::Vector3 goal_vec(goal_position.x - current_pose.pose.position.x,
                            goal_position.y - current_pose.pose.position.y,
                            0.0);
      tf2::Quaternion current_orientation;
      tf2::fromMsg(current_pose.pose.orientation, current_orientation);
      tf2::Matrix3x3 rot_matrix(current_orientation);
      tf2::Vector3 goal_in_robot_frame = rot_matrix.transpose() * goal_vec;

      const double error_x = goal_in_robot_frame.x();
      double linear_speed_x = std::clamp(linear_kp_ * error_x, -max_linear_speed_, max_linear_speed_);

      const double error_y = goal_in_robot_frame.y();
      double linear_speed_y = std::clamp(linear_kp_ * error_y, -max_linear_speed_, max_linear_speed_);
      cmd_vel.linear.x = linear_speed_x;
      cmd_vel.linear.y = linear_speed_y;
    }

    // publish
    cmd_vel_pub_->publish(cmd_vel);

    loop_rate.sleep();
  }
}

geometry_msgs::msg::PoseStamped AdjustmentActionServer::getCurrentPose()
{
  geometry_msgs::msg::TransformStamped transform;

  try {
    transform = tf_buffer_->lookupTransform(
      global_frame_,
      robot_base_frame_,
      tf2::TimePointZero);
  } catch (tf2::TransformException & ex) {
    RCLCPP_ERROR(get_logger(), "AdjustmentActionServer: Transform exception: %s", ex.what());
    throw;
  }

  geometry_msgs::msg::PoseStamped pose;
  pose.header = transform.header;
  pose.pose.position.x = transform.transform.translation.x;
  pose.pose.position.y = transform.transform.translation.y;
  pose.pose.position.z = transform.transform.translation.z;
  pose.pose.orientation = transform.transform.rotation;

  return pose;
}

double AdjustmentActionServer::calculateDistance(
  const geometry_msgs::msg::PoseStamped & current,
  const geometry_msgs::msg::PoseStamped & target)
{
  double dx = target.pose.position.x - current.pose.position.x;
  double dy = target.pose.position.y - current.pose.position.y;
  return std::sqrt(dx * dx + dy * dy);
}

double AdjustmentActionServer::calculateAngleDifference(
  const geometry_msgs::msg::PoseStamped & current,
  const geometry_msgs::msg::PoseStamped & target)
{
  double current_yaw = tf2::getYaw(current.pose.orientation);
  double target_yaw = tf2::getYaw(target.pose.orientation);

  double diff = target_yaw - current_yaw;

  // Normalize to [-pi, pi]
  while (diff > M_PI) diff -= 2.0 * M_PI;
  while (diff < -M_PI) diff += 2.0 * M_PI;

  return diff;
}

}  // namespace custom_adjustment

#include "rclcpp_components/register_node_macro.hpp"
RCLCPP_COMPONENTS_REGISTER_NODE(custom_adjustment::AdjustmentActionServer)
