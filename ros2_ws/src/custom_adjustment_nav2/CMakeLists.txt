cmake_minimum_required(VERSION 3.8)
project(custom_adjustment_nav2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(std_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(nav2_util REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_behaviors REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(behaviortree_cpp REQUIRED)
find_package(nav2_behavior_tree REQUIRED)
find_package(rclcpp_components REQUIRED)

# Generate action interfaces
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Adjust.action"
  DEPENDENCIES
  geometry_msgs
  builtin_interfaces
  ADD_LINTER_TESTS
)


# BT Node Plugin
add_library(custom_adjustment_bt_plugin SHARED
  src/custom_adjustment_bt_node.cpp
)

target_include_directories(custom_adjustment_bt_plugin PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

target_compile_features(custom_adjustment_bt_plugin PUBLIC c_std_99 cxx_std_17)

ament_target_dependencies(custom_adjustment_bt_plugin
  rclcpp
  rclcpp_action
  geometry_msgs
  nav2_msgs
  nav2_util
  tf2
  tf2_geometry_msgs
  behaviortree_cpp
  nav2_behavior_tree
)

# Link BT plugin against generated action interfaces
rosidl_get_typesupport_target(cpp_typesupport_target_bt ${PROJECT_NAME} "rosidl_typesupport_cpp")
target_link_libraries(custom_adjustment_bt_plugin "${cpp_typesupport_target_bt}")


# Adjustment Action Server
add_library(adjustment_action_server SHARED
  src/adjustment_action_server.cpp
)

target_include_directories(adjustment_action_server PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

target_compile_features(adjustment_action_server PUBLIC c_std_99 cxx_std_17)

ament_target_dependencies(adjustment_action_server
  rclcpp
  rclcpp_action
  rclcpp_components
  geometry_msgs
  tf2_ros
  tf2
  tf2_geometry_msgs
)

# Link against generated action interfaces
rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} "rosidl_typesupport_cpp")
target_link_libraries(adjustment_action_server "${cpp_typesupport_target}")

# Register as component
rclcpp_components_register_node(adjustment_action_server
  PLUGIN "custom_adjustment::AdjustmentActionServer"
  EXECUTABLE adjustment_action_server_node
)

install(TARGETS custom_adjustment_bt_plugin adjustment_action_server
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include/
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

# Export dependencies
ament_export_include_directories(include/${PROJECT_NAME})
ament_export_libraries(custom_adjustment_bt_plugin adjustment_action_server)
ament_export_dependencies(
  rclcpp
  rclcpp_action
  rclcpp_components
  rclcpp_lifecycle
  geometry_msgs
  nav2_msgs
  nav2_util
  nav2_behavior_tree
  behaviortree_cpp
  tf2
  tf2_ros
  tf2_geometry_msgs
)

ament_package()
