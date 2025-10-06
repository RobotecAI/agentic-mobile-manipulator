from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="mobile_manipulator_hmi",
                executable="utilization_node",
            ),
            Node(
                package="mobile_manipulator_hmi",
                executable="MobileManipulatorHMI",
            ),
        ]
    )
