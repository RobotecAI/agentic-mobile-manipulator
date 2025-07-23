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
from pprint import pprint



def generate_launch_description():

    use_sim_time = { "use_sim_time": True}


    # robotnik_xacro_path = os.path.join(
    #     get_package_share_directory('robotnik_description'),
    #     'robots','rbkairos',
    #     'rbkairos_plus.urdf.xacro'
    # )

    # robot_description_content = Command(
    #     [
    #         FindExecutable(name="xacro"),
    #         " ",
    #         robotnik_xacro_path,
    #         " namespace:=ego",
    #         " prefix:=ego",
    #         " ur_type:=ur10",
    #         " gazebo_classic:=false",
    #         " gazebo_ignition:=false",
    #     ]
    # )

    # robot_description_param = ParameterValue(robot_description_content, value_type=str)

    moveit_config = MoveItConfigsBuilder("rbkairos", package_name="robotec_kairos_ur10").to_moveit_configs()
    run_move_group_node = Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[moveit_config.to_dict() | use_sim_time],
        )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("robotec_kairos_ur10"),
        "config",
        "robotec_launch.rviz"
    ])

    pprint (moveit_config)


    pprint (moveit_config.joint_limits)
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )


    rgbd_pc = ComposableNodeContainer(
            name='container0',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[
                ComposableNode(
                    package='depth_image_proc',
                    plugin='depth_image_proc::PointCloudXyzrgbNode',
                    name='point_cloud_xyzrgb_node',
                    remappings=[('rgb/camera_info', '/rgbd_camera/camera_info'),
                                ('rgb/image_rect_color', '/rgbd_camera/camera_image_color'),
                                ('depth_registered/image_rect','/rgbd_camera/camera_image_depth'),
                                ('/points','/rgbd_camera/pointcloud')],
                    parameters=[
                        {'use_sim_time': True},
                        {'approximate_sync': True}
                    ]
                ),
            ],
            output='screen',
            parameters=[{'use_sim_time': True, 'approximate_sync': True}]
    
        )

    nodes_to_start = [
        run_move_group_node,
        rviz_node,
        rgbd_pc
    ]

    return LaunchDescription(nodes_to_start)
