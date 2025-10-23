
#include <string>
#include <memory>
#include <cmath>

#include "custom_adjustment_nav2/custom_adjustment_bt_node.hpp"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace nav2_behavior_tree
{

  CustomAdjustmentAction::CustomAdjustmentAction(
    const std::string & xml_tag_name,
    const std::string & action_name,
    const BT::NodeConfiguration & conf)
  : BtActionNode<custom_adjustment_nav2::action::Adjust>(xml_tag_name, action_name, conf)
  {
  }

  void CustomAdjustmentAction::initialize()
  {
    double position_tol, orientation_tol;

    RCLCPP_INFO(node_->get_logger(), "CustomAdjustmentAction::initialize() - Initializing adjustment parameters.");

    getInput("position_tolerance", position_tol);
    getInput("orientation_tolerance", orientation_tol);

    // Get navigation goal and set it as target
    geometry_msgs::msg::PoseStamped goal_pose;
    if (getNavigationGoal(goal_pose)) {
      RCLCPP_INFO(node_->get_logger(), "Setting adjustment target to navigation goal: x=%.3f, y=%.3f, yaw=%.3f",
        goal_pose.pose.position.x,
        goal_pose.pose.position.y,
        tf2::getYaw(goal_pose.pose.orientation));

      goal_.target_pose = goal_pose;
      goal_.position_tolerance = static_cast<float>(position_tol);
      goal_.orientation_tolerance = static_cast<float>(orientation_tol);
    } else {
      RCLCPP_WARN(node_->get_logger(), "Could not retrieve navigation goal for adjustment");
    }
  }

  void CustomAdjustmentAction::on_tick()
  {
    RCLCPP_INFO(node_->get_logger(), "CustomAdjustmentAction::on_tick() - Requesting robot adjustment");

    if (!BT::isStatusActive(status())) {
      initialize();
    }

    increment_recovery_count();
  }


  bool CustomAdjustmentAction::getNavigationGoal(geometry_msgs::msg::PoseStamped & goal)
  {
    // Try to get the goal from the BT blackboard
    if (config().blackboard->get<geometry_msgs::msg::PoseStamped>("goal", goal)) {
      RCLCPP_INFO(node_->get_logger(), "Retrieved navigation goal from blackboard");
      return true;
    }

    // Alternative: try "goals" (for multiple goals)
    std::vector<geometry_msgs::msg::PoseStamped> goals;
    if (config().blackboard->get<std::vector<geometry_msgs::msg::PoseStamped>>("goals", goals) && !goals.empty()) {
      goal = goals.back();  // Use the last/current goal
      RCLCPP_INFO(node_->get_logger(), "Retrieved navigation goal from goals array");
      return true;
    }

    RCLCPP_WARN(node_->get_logger(), "Could not find navigation goal in BT blackboard");
    return false;
  }

}  // namespace nav2_behavior_tree

#include "behaviortree_cpp/bt_factory.h"

extern "C" __attribute__((visibility("default"))) void BT_RegisterNodesFromPlugin(BT::BehaviorTreeFactory& factory)
{
  BT::NodeBuilder builder =
    [](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<nav2_behavior_tree::CustomAdjustmentAction>(name, "adjust", config);
    };

  factory.registerBuilder<nav2_behavior_tree::CustomAdjustmentAction>("CustomAdjustment", builder);
}
