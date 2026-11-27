# Copyright (C) 2026 Advanced Micro Devices, Inc.
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

"""Publishes zero states for the wheel joints, which the simulator does not put on /joint_states.

Without them MoveIt never has the complete robot state and warns on every planning scene
update. Each message reuses the stamp of the simulator message it follows, so all joint
states stay on sim time.
"""

import rclpy
from sensor_msgs.msg import JointState

WHEELS = [
    f"ego{w}_wheel_joint"
    for w in ("back_left", "back_right", "front_left", "front_right")
]


def main():
    rclpy.init()
    node = rclpy.create_node("wheel_joint_states")
    pub = node.create_publisher(JointState, "/joint_states", 10)

    def republish(msg: JointState):
        if (
            WHEELS[0] in msg.name
        ):  # our own message, or the sim started publishing wheels
            return
        pub.publish(
            JointState(header=msg.header, name=WHEELS, position=[0.0] * len(WHEELS))
        )

    node.create_subscription(JointState, "/joint_states", republish, 10)
    rclpy.spin(node)


if __name__ == "__main__":
    main()
