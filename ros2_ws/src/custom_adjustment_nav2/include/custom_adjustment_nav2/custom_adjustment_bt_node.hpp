#ifndef CUSTOM_ADJUSTMENT__CUSTOM_ADJUSTMENT_BT_NODE_HPP_
#define CUSTOM_ADJUSTMENT__CUSTOM_ADJUSTMENT_BT_NODE_HPP_

#include <string>

#include "nav2_behavior_tree/bt_action_node.hpp"
#include "custom_adjustment_nav2/action/adjust.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "tf2/utils.h"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

namespace nav2_behavior_tree
{

/**
 * @brief A nav2_behavior_tree::BtActionNode class that wraps custom_adjustment_nav2::action::Adjust
 */
class CustomAdjustmentAction : public BtActionNode<custom_adjustment_nav2::action::Adjust>
{
public:
  /**
   * @brief A constructor for nav2_behavior_tree::CustomAdjustmentAction
   * @param xml_tag_name Name for the XML tag for this node
   * @param action_name Action name this node creates a client for
   * @param conf BT node configuration
   */
  CustomAdjustmentAction(
    const std::string & xml_tag_name,
    const std::string & action_name,
    const BT::NodeConfiguration & conf);

  /**
   * @brief Function to perform some user-defined operation on tick
   */
  void on_tick() override;

  /**
   * @brief Function to read parameters and initialize class variables
   */
  void initialize();

  /**
   * @brief Creates list of BT ports
   * @return BT::PortsList Containing basic ports along with node-specific ports
   */
  static BT::PortsList providedPorts()
  {
    return providedBasicPorts(
      {
        BT::InputPort<double>("position_tolerance", 0.1, "Position tolerance in meters"),
        BT::InputPort<double>("orientation_tolerance", 0.1, "Orientation tolerance in radians")
      });
  }

private:
  bool getNavigationGoal(geometry_msgs::msg::PoseStamped & goal);
};

}  // namespace nav2_behavior_tree

#endif  // CUSTOM_ADJUSTMENT__CUSTOM_ADJUSTMENT_BT_NODE_HPP_
