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
