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

from demo_msgs.msg import VlmDescription
from rai.communication.ros2 import ROS2Connector, ROS2Message
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import Image


def publish_vlm_description(
    connector: ROS2Connector, image: Image, description: str, source: str
):
    vlm_description = VlmDescription(
        image=image, description=description, source=source
    )
    connector.send_message(
        ROS2Message(payload=message_to_ordereddict(vlm_description)),
        target="/vlm_topic",
        msg_type="demo_msgs/msg/VlmDescription",
    )
