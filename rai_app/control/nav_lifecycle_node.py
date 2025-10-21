# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Developed by Robotec.ai sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rclpy
from geometry_msgs.msg import Twist
from nav2_msgs.srv import ManageLifecycleNodes
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.node import Node
from std_msgs.msg import Empty


class Nav2Lifecycle(Node):
    def __init__(self):
        super().__init__("nav2_lifecycle_client_node")
        service_name = "/lifecycle_manager_navigation/manage_nodes"
        self.cli = self.create_client(ManageLifecycleNodes, service_name)

        callback_group = MutuallyExclusiveCallbackGroup()
        self.emergency_sub = self.create_subscription(
            Empty,
            "/emergency_stop",
            self.emergency_stop_callback,
            10,
            callback_group=callback_group,
        )
        self.resume_sub = self.create_subscription(
            Empty,
            "/resume_navigation",
            self.resume_navigation,
            10,
            callback_group=callback_group,
        )

        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f"Waiting for {service_name} service...")

    def lifecycle_node_stop_callback(self, future):
        response = future.result()
        if response is not None:
            self.get_logger().info(f"Stop success={response.success}")
        else:
            self.get_logger().error("Stop failed!")
        self.zero_cmd_vel()

    def emergency_stop_callback(self, msg):
        self.pause()

    def pause(self):
        req = ManageLifecycleNodes.Request()
        req.command = ManageLifecycleNodes.Request.PAUSE
        future = self.cli.call_async(req)
        future.add_done_callback(self.lifecycle_node_stop_callback)

    def resume_navigation(self, msg):
        self.response = None
        req = ManageLifecycleNodes.Request()
        req.command = ManageLifecycleNodes.Request.STARTUP
        future = self.cli.call_async(req)
        future.add_done_callback(self.resume_navigation_callback)

    def resume_navigation_callback(self, future):
        response = future.result()
        if response is not None:
            self.get_logger().info(f"Resuming success={response.success}")
        else:
            self.get_logger().error("Resuming failed!")

    def zero_cmd_vel(self):
        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.cmd_vel_pub.publish(msg)
        self.get_logger().info("Zeroing cmd_vel DONE.")


def main():
    rclpy.init()
    node = Nav2Lifecycle()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
