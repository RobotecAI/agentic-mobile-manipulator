### visualize slots in rviz
import csv

import rclpy
from geometry_msgs.msg import Pose, Vector3
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, Header
from visualization_msgs.msg import Marker, MarkerArray


class SlotPublisher(Node):
    def __init__(self, filename: str):
        super().__init__("slot_publisher")
        self.filename = filename
        self.pub = self.create_publisher(MarkerArray, "/slot_markers", 10)
        self.timer = self.create_timer(1.0, self.publish_slots)

        self.markers = MarkerArray()

        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Cube marker
                marker = Marker()
                marker.header = Header(
                    frame_id="map", stamp=self.get_clock().now().to_msg()
                )
                marker.ns = "slots"
                marker.id = i
                marker.type = 0
                marker.action = Marker.ADD
                marker.pose = Pose()
                marker.pose.position.x = float(row["x"])
                marker.pose.position.y = float(row["y"])
                marker.pose.position.z = float(row["z"])
                marker.pose.orientation.x = float(row["qx"])
                marker.pose.orientation.y = float(row["qy"])
                marker.pose.orientation.z = float(row["qz"])
                marker.pose.orientation.w = float(row["qw"])
                marker.scale = Vector3(x=0.3, y=0.05, z=0.05)
                marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
                self.markers.markers.append(marker)

                # Text marker
                text = Marker()
                text.header = marker.header
                text.ns = "labels"
                text.id = i * 2 + 1
                text.type = Marker.TEXT_VIEW_FACING
                text.action = Marker.ADD
                text.pose = marker.pose
                text.pose.position.z += 0.3
                text.scale = Vector3(z=0.1)
                text.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
                text.text = row["slot_name"]
                self.markers.markers.append(text)

    def publish_slots(self):
        self.pub.publish(self.markers)


def main():
    rclpy.init()
    node = SlotPublisher(filename="scripts/resources/slots.csv")
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
