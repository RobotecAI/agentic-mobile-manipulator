cmake_minimum_required(VERSION 3.16)
project(kairos_hmi_qml VERSION 0.1.0 LANGUAGES CXX)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(demo_msgs REQUIRED)
find_package(rai_interfaces REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Quick Qml Gui)

add_executable(kairos_hmi_qml
  src/main.cpp
  src/RosBridge.cpp
  src/RosBridge.h
  src/CameraImageProvider.h
  qml.qrc
)

target_link_libraries(kairos_hmi_qml
  Qt5::Quick
  Qt5::Qml
  Qt5::Gui
)

ament_target_dependencies(kairos_hmi_qml
  rclcpp
  sensor_msgs
  nav_msgs
  geometry_msgs
  std_msgs
  std_srvs
  rcl_interfaces
  tf2
  tf2_ros
  demo_msgs
  rai_interfaces
)

install(TARGETS kairos_hmi_qml DESTINATION lib/${PROJECT_NAME})

ament_package()
