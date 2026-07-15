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

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(QT NAMES Qt5 REQUIRED COMPONENTS Widgets)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets)


# --- ROS2 / image transport dependencies ---
# These assume you have sourced your ROS2 installation (e.g. source /opt/ros/humble/setup.bash)
# and installed packages like ros-<distro>-image-transport, ros-<distro>-compressed-image-transport, ros-<distro>-cv-bridge.
# If you get errors like "Could not find package X", install the corresponding ros package and source the ROS 2 environment.
find_package(rclcpp REQUIRED)                        # core ROS2 C++ client library
find_package(sensor_msgs REQUIRED)                   # sensor message types
find_package(nav_msgs REQUIRED)                      # navigation message types (OccupancyGrid)
find_package(geometry_msgs REQUIRED)                 # geometry message types (Twist)
find_package(rcl_interfaces REQUIRED)                # rcl interface message types (Log)
find_package(tf2_ros REQUIRED)                       # tf2 transform listener
find_package(tf2 REQUIRED)                           # tf2 core
find_package(image_transport REQUIRED)               # image_transport API
find_package(std_srvs REQUIRED)                        # for using standard ROS services
find_package(cv_bridge REQUIRED)                     # conversion between ROS images and OpenCV
find_package(OpenCV REQUIRED)
find_package(demo_msgs REQUIRED)               # custom Utilization message
find_package(rai_interfaces REQUIRED)               # custom Utilization message

# add source directory to include path
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# --- nlohmann/json dependency (from conda-forge) ---
find_package(nlohmann_json REQUIRED)

# --- toml++ dependency (config.toml parsing, from conda-forge) ---
find_package(tomlplusplus REQUIRED)

set(PROJECT_SOURCES
        main.cpp
        ZoomableGraphicsView.h
        ZoomableGraphicsView.cpp
        Config.h
        ModelConfig.h
        ModelConfig.cpp
        LogItemWidget.h
        LogItemWidget.cpp
        LogView.h
        LogView.cpp
        LogQueue.h
        LogQueue.cpp
        hmiWindow.cpp
        hmiWindow.h
        hmiWindow.ui
        TaskDialog.cpp
        TaskDialog.h
        resources.qrc
        ParseRaiData.cpp
        ParseRaiData.h
)

if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_add_executable(MobileManipulatorHMI
        MANUAL_FINALIZATION
        ${PROJECT_SOURCES}
    )
else()
    add_executable(MobileManipulatorHMI
        ${PROJECT_SOURCES}
    )
endif()

target_link_libraries(MobileManipulatorHMI PRIVATE Qt${QT_VERSION_MAJOR}::Widgets) 

target_link_libraries(MobileManipulatorHMI PRIVATE
        rclcpp::rclcpp
        sensor_msgs::sensor_msgs__rosidl_typesupport_cpp
        nav_msgs::nav_msgs__rosidl_typesupport_cpp
        geometry_msgs::geometry_msgs__rosidl_typesupport_cpp
        rcl_interfaces::rcl_interfaces__rosidl_typesupport_cpp
        std_srvs::std_srvs__rosidl_typesupport_cpp
        demo_msgs::demo_msgs__rosidl_typesupport_cpp
        rai_interfaces::rai_interfaces__rosidl_typesupport_cpp
        tf2_ros::tf2_ros
        tf2::tf2
        image_transport::image_transport
        cv_bridge::cv_bridge
        ${OpenCV_LIBS}           # OpenCV provides targets like OpenCV::Core, but ${OpenCV_LIBS} is usually set
        nlohmann_json::nlohmann_json
        tomlplusplus::tomlplusplus
)

# Install targets
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
    Qt${QT_VERSION_MAJOR}::Widgets
    nlohmann_json::nlohmann_json
  )
endif()


