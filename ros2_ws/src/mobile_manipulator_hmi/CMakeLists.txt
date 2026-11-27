cmake_minimum_required(VERSION 3.8)

project(mobile_manipulator_hmi VERSION 0.1 LANGUAGES CXX)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

# --- Install Python scripts ---
install(
  PROGRAMS
    mobile_manipulator_hmi/utilization_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME utilization_node
)

# --- Install launch files ---
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt5 REQUIRED COMPONENTS Gui Qml Quick QuickControls2 Network)

find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosgraph_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2 REQUIRED)
find_package(std_srvs REQUIRED)
find_package(demo_msgs REQUIRED)
find_package(rai_interfaces REQUIRED)
find_package(nlohmann_json REQUIRED)    # from conda-forge
find_package(tomlplusplus REQUIRED)     # config.toml parsing, from conda-forge

include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# The UI is QML (qml/, bundled through qml.qrc); RosBridge is its only link to ROS 2.
add_executable(MobileManipulatorHMI
  main.cpp
  RosBridge.h
  RosBridge.cpp
  AgentEventModel.h
  AgentEventModel.cpp
  RosImageProvider.h
  ModelConfig.h
  ModelConfig.cpp
  ParseRaiData.h
  ParseRaiData.cpp
  qml.qrc
)

target_link_libraries(MobileManipulatorHMI PRIVATE
  Qt5::Gui Qt5::Qml Qt5::Quick Qt5::QuickControls2 Qt5::Network
  rclcpp::rclcpp
  ${sensor_msgs_TARGETS}
  ${nav_msgs_TARGETS}
  ${geometry_msgs_TARGETS}
  ${std_msgs_TARGETS}
  ${rosgraph_msgs_TARGETS}
  ${rcl_interfaces_TARGETS}
  ${std_srvs_TARGETS}
  ${demo_msgs_TARGETS}
  ${rai_interfaces_TARGETS}
  tf2_ros::tf2_ros
  tf2::tf2
  nlohmann_json::nlohmann_json
  tomlplusplus::tomlplusplus
)

install(TARGETS MobileManipulatorHMI
  DESTINATION lib/${PROJECT_NAME})

# --- Testing ---
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  # Test for ParseRaiData
  ament_add_gtest(test_parse_rai_data
    test/test_parse_rai_data.cpp
    ParseRaiData.cpp
  )

  target_include_directories(test_parse_rai_data PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
  )

  target_link_libraries(test_parse_rai_data
    Qt5::Core
    nlohmann_json::nlohmann_json
  )
endif()


