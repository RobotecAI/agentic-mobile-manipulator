#!/usr/bin/env python3

import argparse
from typing import Optional

import rclpy
from geometry_msgs.msg import Vector3
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_services,
)
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from simulation_interfaces.msg import EntityState
from simulation_interfaces.srv import GetEntityState
from std_msgs.msg import ColorRGBA, Header
from visualization_msgs.msg import Marker, MarkerArray

from rai_app.environment import SceneManager


class EntitiesAndSlotsPublisher(Node):
    """Publisher that reads entity states and slots, publishes them as markers to RViz"""

    def __init__(
        self,
        namespace: str = "",
        update_rate: float = 10.0,
        slots_file: str = "scripts/resources/slots.csv",
    ):
        super().__init__("entities_and_slots_publisher")

        self.namespace = namespace
        self.update_rate = update_rate
        self.slots_file = slots_file
        self.connector = ROS2Connector()

        # Create publishers
        self.entities_marker_pub = self.create_publisher(
            MarkerArray, f"{namespace}/entities_markers", 10
        )
        self.slots_marker_pub = self.create_publisher(
            MarkerArray, f"{namespace}/slot_markers", 10
        )

        self.scene_manager = SceneManager(
            connector=self.connector,
            slots_file=slots_file,
            spawnables_file="scripts/resources/spawnables.csv",
        )

        # Entity tracking
        self.last_entities = set()

        # Wait for required services
        wait_for_ros2_services(self.connector, ["/get_entities", "/get_entity_state"])

        self.get_logger().info("Entities and slots publisher initialized")

    def get_entity_type_from_name(self, entity_name: str) -> str:
        """Determine entity type from entity name"""
        if "ego" in entity_name.lower() or "robot" in entity_name.lower():
            return "robot"
        elif "human" in entity_name.lower() or "worker" in entity_name.lower():
            return "human"
        elif "box" in entity_name.lower() or "cardboard" in entity_name.lower():
            return "box"
        elif "barrel" in entity_name.lower():
            return "barrel"
        elif "ladder" in entity_name.lower():
            return "ladder"
        elif "oil" in entity_name.lower() or "spill" in entity_name.lower():
            return "oil_spill"
        elif "fire" in entity_name.lower() or "extinguisher" in entity_name.lower():
            return "fire_extinguisher"
        elif "paint" in entity_name.lower() or "can" in entity_name.lower():
            return "paint_can"
        elif "bucket" in entity_name.lower():
            return "bucket"
        elif "canister" in entity_name.lower():
            return "canister"
        else:
            return "unknown"

    def create_marker_for_entity(
        self, entity_name: str, entity_state: EntityState, entity_type: str
    ) -> tuple:
        """Create a marker for a specific entity based on its type"""
        entity_id = hash(entity_name) % 10000

        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = f"entities_{entity_type}"
        marker.id = entity_id
        marker.action = Marker.ADD
        marker.pose = entity_state.pose

        # Set color and scale based on entity type
        if entity_type == "robot":
            marker.type = Marker.CUBE
            marker.scale = Vector3(x=0.8, y=0.6, z=1.2)
            marker.color = ColorRGBA(r=0.0, g=0.5, b=1.0, a=0.8)
        elif entity_type == "human":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.6, y=0.6, z=1.8)
            marker.color = ColorRGBA(r=1.0, g=0.8, b=0.6, a=0.8)
        elif entity_type == "box":
            marker.type = Marker.CUBE
            marker.scale = Vector3(x=0.4, y=0.3, z=0.2)
            marker.color = ColorRGBA(r=0.6, g=0.4, b=0.2, a=0.8)
        elif entity_type == "barrel":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.5, y=0.5, z=0.8)
            marker.color = ColorRGBA(r=0.8, g=0.8, b=0.8, a=0.8)
        elif entity_type == "ladder":
            marker.type = Marker.CUBE
            marker.scale = Vector3(x=0.1, y=0.1, z=2.0)
            marker.color = ColorRGBA(r=0.3, g=0.3, b=0.3, a=0.8)
        elif entity_type == "oil_spill":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=1.0, y=1.0, z=0.05)
            marker.color = ColorRGBA(r=0.2, g=0.2, b=0.2, a=0.6)
        elif entity_type == "fire_extinguisher":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.2, y=0.2, z=0.6)
            marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.8)
        elif entity_type == "paint_can":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.15, y=0.15, z=0.2)
            marker.color = ColorRGBA(r=0.5, g=0.5, b=0.5, a=0.8)
        elif entity_type == "bucket":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.3, y=0.3, z=0.25)
            marker.color = ColorRGBA(r=0.7, g=0.7, b=0.7, a=0.8)
        elif entity_type == "canister":
            marker.type = Marker.CYLINDER
            marker.scale = Vector3(x=0.2, y=0.2, z=0.4)
            marker.color = ColorRGBA(r=0.4, g=0.4, b=0.4, a=0.8)
        else:  # unknown
            marker.type = Marker.SPHERE
            marker.scale = Vector3(x=0.3, y=0.3, z=0.3)
            marker.color = ColorRGBA(r=0.5, g=0.5, b=0.5, a=0.6)

        # Text marker
        text_marker = Marker()
        text_marker.header = marker.header
        text_marker.ns = f"entities_text_{entity_type}"
        text_marker.id = entity_id + 10000
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD
        text_marker.pose = marker.pose
        text_marker.pose.position.z += marker.scale.z / 2 + 0.2
        text_marker.scale = Vector3(x=0.0, y=0.0, z=0.1)
        text_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        text_marker.text = entity_name

        # Arrow marker
        arrow_marker = Marker()
        arrow_marker.header = marker.header
        arrow_marker.ns = f"entities_arrow_{entity_type}"
        arrow_marker.id = entity_id + 20000
        arrow_marker.type = Marker.ARROW
        arrow_marker.action = Marker.ADD
        arrow_marker.pose = entity_state.pose
        arrow_length = max(marker.scale.x, marker.scale.y) * 1.2
        arrow_marker.scale = Vector3(x=arrow_length, y=0.1, z=0.1)
        arrow_marker.color = ColorRGBA(r=1.0, g=1.0, b=0.0, a=0.9)

        return marker, text_marker, arrow_marker

    def get_entity_state(self, entity_name: str) -> Optional[EntityState]:
        """Get state of a specific entity"""
        try:
            req = GetEntityState.Request()
            req.entity = entity_name
            response = self.connector.call_service(
                ROS2Message(payload=message_to_ordereddict(req)),
                target="/get_entity_state",
                msg_type="simulation_interfaces/srv/GetEntityState",
                timeout_sec=3.0,
            ).payload
            return response.state
        except Exception as e:
            self.get_logger().warn(f"Failed to get state for {entity_name}: {e}")
            return None

    def publish_entities_markers(self):
        """Get all entities and publish their markers"""
        entities = self.scene_manager.get_entities(name_filter="box")
        entities = self.scene_manager.filter_out_gripping_point_entites(
            entities=entities
        )
        if not entities:
            self.get_logger().debug("No entities found")
            return

        # Assign entities to slots
        self.scene_manager.assign_entities_to_slots(entities=entities)
        marker_array = MarkerArray()

        for entity_name, entity_state in entities.items():
            if entity_state is None:
                continue

            entity_type = self.get_entity_type_from_name(entity_name)
            marker, text_marker, arrow_marker = self.create_marker_for_entity(
                entity_name, entity_state, entity_type
            )

            marker_array.markers.append(marker)
            marker_array.markers.append(text_marker)
            marker_array.markers.append(arrow_marker)

        self.entities_marker_pub.publish(marker_array)
        self.get_logger().debug(
            f"Published {len(marker_array.markers)} markers for {len(entities)} entities"
        )

    def publish_slots_markers(self):
        """Publish slot markers with color based on occupancy"""
        marker_array = MarkerArray()
        marker_id = 0

        for coll_name, collection in self.scene_manager.slots_collections.items():
            for slot_name, slot in collection.slots.items():
                # Determine if slot is occupied
                is_occupied = slot.get_obj_name() is not None

                # Cube marker for slot
                marker = Marker()
                marker.header = Header(
                    frame_id="odom", stamp=self.get_clock().now().to_msg()
                )
                marker.ns = "slots"
                marker.id = marker_id
                marker.type = Marker.ARROW
                marker.action = Marker.ADD
                marker.pose = slot.origin_pose
                marker.scale = Vector3(x=0.3, y=0.05, z=0.05)

                # Color based on occupancy: green if occupied, red if empty
                if is_occupied:
                    marker.color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0)
                else:
                    marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)

                marker_array.markers.append(marker)

                # Text marker for slot name
                text = Marker()
                text.header = marker.header
                text.ns = "slot_labels"
                text.id = marker_id + 100000
                text.type = Marker.TEXT_VIEW_FACING
                text.action = Marker.ADD
                text.pose = slot.origin_pose
                text.scale = Vector3(z=0.1)
                text.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)

                # Show entity name if occupied
                if is_occupied:
                    text.text = f"{slot_name}\n({slot.get_obj_name()})"
                else:
                    text.text = slot_name

                marker_array.markers.append(text)

                marker_id += 1

        self.slots_marker_pub.publish(marker_array)
        self.get_logger().debug(f"Published {len(marker_array.markers)} slot markers")

    def run(self):
        """Main run loop"""
        self.get_logger().info("Starting entities and slots publisher...")

        # Create timers for periodic updates
        _ = self.create_timer(1.0 / self.update_rate, self.publish_entities_markers)
        _ = self.create_timer(1.0 / self.update_rate, self.publish_slots_markers)

        try:
            rclpy.spin(self)
        except KeyboardInterrupt:
            self.get_logger().info("Shutting down publisher...")
        finally:
            self.connector.shutdown()


@ROS2Context()
def main():
    parser = argparse.ArgumentParser(
        description="Publish entity and slot states as marker arrays to RViz"
    )
    parser.add_argument(
        "--namespace", type=str, default="", help="ROS2 namespace for topics"
    )
    parser.add_argument(
        "--update_rate",
        type=float,
        default=10.0,
        help="Update rate in Hz (default: 10.0)",
    )
    parser.add_argument(
        "--slots_file",
        type=str,
        default="scripts/resources/slots.csv",
        help="Path to slots CSV file",
    )
    args = parser.parse_args()

    publisher = EntitiesAndSlotsPublisher(
        namespace=args.namespace,
        update_rate=args.update_rate,
        slots_file=args.slots_file,
    )
    publisher.run()


if __name__ == "__main__":
    main()
