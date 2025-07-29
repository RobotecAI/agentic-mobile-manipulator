from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder


import os
import yaml


def generate_launch_description():

    declared_arguments = []

    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except (
        EnvironmentError
    ):  # parent of IOError, OSError *and* WindowsError where available
        return None


def launch_setup(context, *args, **kwargs):

    use_sim_time = {"use_sim_time": True}
    moveit_config = (
        MoveItConfigsBuilder("moveit_resources_panda")
        .robot_description(file_path="config/panda.urdf.xacro")
        .trajectory_execution(file_path="config/gripper_moveit_controllers.yaml")
        .planning_scene_monitor(
            publish_robot_description=True, publish_robot_description_semantic=True
        )
        .planning_pipelines(
            pipelines=["ompl", "chomp", "pilz_industrial_motion_planner"]
        )
        .to_moveit_configs()
    )
    moveit_config.planning_pipelines["ompl"]["panda_arm"][
        "enforce_constrained_state_space"
    ] = True
    moveit_config.planning_pipelines["ompl"]["panda_arm"][
        "projection_evaluator"
    ] = "joints(panda_joint1,panda_joint2)"
    moveit_config.planning_pipelines["ompl"]["panda_arm_hand"][
        "enforce_constrained_state_space"
    ] = True
    moveit_config.planning_pipelines["ompl"]["panda_arm_hand"][
        "projection_evaluator"
    ] = "joints(panda_joint1,panda_joint2)"

    # Start the actual move_group node/action server
    run_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict() | use_sim_time],
    )

    # Static TF
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "world", "panda_link0"],
    )

    # rgbd_pc = ComposableNodeContainer(
    #     name="container0",
    #     namespace="",
    #     package="rclcpp_components",
    #     executable="component_container",
    #     composable_node_descriptions=[
    #         ComposableNode(
    #             package="depth_image_proc",
    #             plugin="depth_image_proc::PointCloudXyzrgbNode",
    #             name="point_cloud_xyzrgb_node",
    #             remappings=[
    #                 ("rgb/camera_info", "/color_camera_info"),
    #                 ("rgb/image_rect_color", "/camera_image_color"),
    #                 ("depth_registered/image_rect", "/camera_image_depth"),
    #                 ("/points", "/pointcloud"),
    #             ],
    #         ),
    #     ],
    #     output="screen",
    #     parameters=[{"use_sim_time": True}],
    # )

    # Publish TF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    nodes_to_start = [
        #        rviz_node,
        static_tf,
        robot_state_publisher,
        run_move_group_node,
        # rgbd_pc,
    ]

    return nodes_to_start
