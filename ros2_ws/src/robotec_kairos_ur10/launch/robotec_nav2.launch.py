import pathlib

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, IfElseSubstitution, EqualsSubstitution
from nav2_common.launch import ReplaceString, RewrittenYaml
from launch_ros.descriptions import ParameterFile

def generate_launch_description():
    nav2_params = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "nav2_params.yaml"
    ])

    robot_namespace = LaunchConfiguration('robot_namespace', default='')

    configured_params = ReplaceString(
        source_file=nav2_params,
        replacements={
            "<robot_namespace>": IfElseSubstitution(
                condition=EqualsSubstitution(robot_namespace, ''),
                if_value='',
                else_value=(robot_namespace, '/')
            )
        }
    ),

    map_file = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "resources",
        "demolevel.yaml"
    ])

    map_pub = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            {'yaml_filename': map_file},
            {'use_sim_time': True}
        ]
    )
    map_lifecycle =   Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{'autostart': True}, {'node_names': ['map_server'] }]
    )
    # Robot's localization problem is already solved issue in the industry.
    gt_map_pub =  Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='odom_to_map_broadcaster',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'map', 'odom'],
        parameters=[{'use_sim_time': True}]
    )


    return LaunchDescription([
        gt_map_pub, 
        map_pub,
        map_lifecycle,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([str(pathlib.Path(
                get_package_share_directory('robotec_kairos_ur10')).joinpath('launch', 'robotec_navigation.launch.py'))]),
            launch_arguments = {
                'params_file': configured_params,
                'use_sim_time': 'True',
                'robot_namespace': robot_namespace,
            }.items()
        )
    ])