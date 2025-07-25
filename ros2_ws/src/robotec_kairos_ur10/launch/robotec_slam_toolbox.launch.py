import pathlib

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
import os
def generate_launch_description():


    robotnik_xacro_path = os.path.join(
        get_package_share_directory('robotnik_description'),
        'robots','rbkairos',
        'rbkairos_plus.urdf.xacro'
    )

    robot_description_content = Command(
        [
            FindExecutable(name="xacro"),
            " ",
            robotnik_xacro_path,
            " namespace:=ego",
            " prefix:=ego",
            " ur_type:=ur10",
            " gazebo_classic:=false",
            " gazebo_ignition:=false",
        ]
    )

    robot_description_param = ParameterValue(robot_description_content, value_type=str)

    rviz_config = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "slam_config.rviz"
    ])

    slam_config = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "slam_params.yaml"
    ])


    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_description_param, 'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='interactive_marker_twist_server',
            executable='marker_server',
            name='marker_teleop',
            output='screen',
            parameters=[{'link_name': 'egobase_link',
                         'use_sim_time': True,
                         'use_stamped_msgs': False,
                         'linear_scale':
                         {
                            'x' : 1.0,
                             'y': 1.0
                         },
                         'max_positive_linear_velocity':
                         {
                             'x' : 1.0,
                             'y': 1.0
                         },
                         'max_negative_linear_velocity':
                         {
                             'x': -1.0,
                             'y': -1.0 
                         }
                         }],
            # remappings=[
            #     ('/cmd_vel', '/cmd_vel')
            # ]
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}]
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([str(pathlib.Path(
                get_package_share_directory('slam_toolbox')).joinpath('launch', 'online_async_launch.py'))]),
            launch_arguments = {
                'slam_params_file': slam_config
            }.items()
        )
    ])