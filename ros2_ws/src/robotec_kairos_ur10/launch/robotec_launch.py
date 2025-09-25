from pathlib import Path
from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import OpaqueFunction
from pprint import pprint
from nav2_common.launch import ReplaceString, RewrittenYaml
from launch_param_builder import load_yaml


def launch_setup(context, *args, **kwargs):
    use_sim_time = { "use_sim_time": True}
    robot_namespace = LaunchConfiguration('robot_namespace', default='')

    namespace_value = robot_namespace.perform(context)
    if namespace_value != '':
        namespace_value = namespace_value + '/'

    joint_limits_yaml_path = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "joint_limits.yaml"
    ]).perform(context)
    joint_limits_params = load_yaml(Path(joint_limits_yaml_path))
    for joint in list(joint_limits_params['joint_limits']):
        joint_limits_params['joint_limits'][f"{namespace_value}{joint}"] = joint_limits_params['joint_limits'].pop(joint)

    moveit_controllers_yaml_path = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "moveit_controllers.yaml"
    ]).perform(context)
    moveit_controllers_params = load_yaml(Path(moveit_controllers_yaml_path))
    controller_names = list(moveit_controllers_params['moveit_simple_controller_manager']['controller_names'])
    for controller in controller_names:
        params = moveit_controllers_params['moveit_simple_controller_manager'].pop(controller)
        params['joints'] = [f"{namespace_value}{joint}" for joint in params['joints']]
        moveit_controllers_params['moveit_simple_controller_manager'][f"{namespace_value}{controller}"] = params
    moveit_controllers_params['moveit_simple_controller_manager']['controller_names'] = [
        f"{namespace_value}{controller}" for controller in controller_names
    ]

    moveit_config = (MoveItConfigsBuilder("rbkairos", package_name="robotec_kairos_ur10")
        .robot_description(
            mappings={
                "namespace": f"{namespace_value}ego",
                "prefix": f"{namespace_value}ego",
                "ur_type": "ur10",
                "gazebo_classic": "false",
                "gazebo_ignition": "false",
            }
        )
        .robot_description_semantic(
            mappings={
                "namespace": f"{namespace_value}ego",
                "prefix": f"{namespace_value}ego",
            }
        )
        .to_moveit_configs()
    )
    moveit_config.joint_limits = {"robot_description_planning": joint_limits_params}

    run_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict() | use_sim_time | moveit_controllers_params],
        remappings=[
            ('/joint_states', (robot_namespace, '/joint_states')),
        ]
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "robotec_launch.rviz"
    ])

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        remappings=[('/scan_rear_left', f'{namespace_value}scan_rear_left'),
                    ('/scan_front_right', f'{namespace_value}scan_front_right')],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    marker_server = Node(
        package='interactive_marker_twist_server',
        executable='marker_server',
        name='marker_teleop',
        output='screen',
        parameters=[{'link_name': f'{namespace_value}egobase_link',
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
        remappings=[
            ('/cmd_vel', (robot_namespace, '/cmd_vel'))
        ]
    )

    return [
        run_move_group_node, 
        rviz_node, 
        marker_server
    ]


def generate_launch_description():
    use_sim_time = { "use_sim_time": True}

    robot_namespace = LaunchConfiguration('robot_namespace', default='')
    
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("robotec_kairos_ur10"),
                "launch",
                "robotec_nav2.launch.py"
            ])
        ),
        launch_arguments = {
            'robot_namespace': robot_namespace,
        }.items()
    )

    nodes_to_start = [
        OpaqueFunction(function=launch_setup),
        nav2_launch,
    ]

    return LaunchDescription(nodes_to_start)
