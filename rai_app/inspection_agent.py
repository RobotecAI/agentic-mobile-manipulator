from __future__ import annotations

import argparse
import base64
import queue
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Literal, Optional, cast

import numpy as np
import rclpy
import rclpy.time
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from llms import get_model
from pydantic import BaseModel, Field
from rai.agents import BaseAgent
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_topics,
)
from rai.messages import (
    HumanMultimodalMessage,
    preprocess_image,
)
from robotec_kairos_ur10.msg import Anomaly
from rosidl_runtime_py import message_to_ordereddict
from sensor_msgs.msg import Image
from tf2_ros import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray

from scripts.scene_manager import SceneManager
from scripts.tools import get_yaw_difference

SYSTEM_PROMPT = "You are an expert in warehouse environment based on AMR camera. You are tested in simulation. You follow strict OSHA regulation: there should be no objects on the warehouse floor. Boxes directly under racks can be on the floor. Bins can be on the floor. Safety equipment can be on the floor. The OSHA guideline is for there to be no tripping hazard."
# PROMPT = "Verify if there is an obstacle on a robot's path. Please don't report typical warehouse envirionemt as obstacles. To be an obstacle a object should be places in an unusual place and obstruct the clear navigation path of the robot. For example a package laying in the pathway might be an obstance and standing rack visible in the image is not."
PROMPT = (
    "Detect if there is an object on the floor. Decide if the object is trash or a box."
)


class AnomalyDescription(BaseModel):
    anomaly_detected: bool = Field(..., description="True if obstacle is detected")
    obstacle_type: Literal["box", "trash"] = Field(
        ..., description="The type of the obstacle"
    )
    anomaly_description: str = Field(
        ...,
        description="A description of the obstacle. Max 20 chars. Leave empty if no obstacle",
    )


class ModelConfig(BaseModel):
    vendor: Literal["openai", "ollama"]
    model: str
    base_url: str | None = None


def save_image_to_disk(b64_img: str, directory: str = "./saved_images") -> str:
    directory_path = Path(directory).resolve()
    if not directory_path.exists():
        directory_path.mkdir(parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_path = directory_path / f"image_{timestamp}.png"
    with image_path.open("wb") as f:
        f.write(base64.b64decode(b64_img))
    return str(image_path)


def are_poses_close(
    pose1: Pose, pose2: Pose, distance: float, rot_degrees: float
) -> bool:
    position_ok = (
        np.linalg.norm(
            np.array([pose1.position.x, pose1.position.y, pose1.position.z])
            - np.array([pose2.position.x, pose2.position.y, pose2.position.z])
        )
        < distance
    )

    yaw_diff = get_yaw_difference(pose1, pose2)
    orientation_ok = yaw_diff < rot_degrees

    return position_ok and orientation_ok


def are_anomalies_close(
    anomaly1: Anomaly, anomaly2: Anomaly, distance: float, rot_degrees: float
) -> bool:
    # NOTE (jmatejcz) model can detect same thing as different types so I think
    # commecting this amtch out is a good idea
    # obstacle_type_match = anomaly1.obstacle_type == anomaly2.obstacle_type
    poses_match = are_poses_close(anomaly1.pose, anomaly2.pose, distance, rot_degrees)
    return poses_match


@dataclass
class InspectionTask:
    b64_img: str
    image: np.ndarray
    img_stamp: rclpy.time.Time
    robot_location_stamp: rclpy.time.Time
    object_pose: Pose


class VlmWarehouseInspector(BaseAgent):
    def __init__(
        self,
        vlm: ChatOllama | ChatOpenAI,
        slots_file: str,
        spawnables_file: str,
        camera_topic: str,
        ego_target_frame: str,
        ego_source_frame: str,
        anomaly_images_dir: Optional[str],
        anomalies_topic: str,
        prompt: str = PROMPT,
        system_prompt: str = SYSTEM_PROMPT,
        match_anomaly_max_distance: float = 0.1,
        match_anomaly_max_yaw_degrees: float = 10.0,
        n_seconds: int = 1,
        debug: bool = True,
    ):
        self.camera_topic = camera_topic
        self.ego_target_frame = ego_target_frame
        self.ego_source_frame = ego_source_frame
        self.anomaly_images_dir = anomaly_images_dir
        self.anomalies_topic = anomalies_topic
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.match_anomaly_max_distance = match_anomaly_max_distance
        self.match_anomaly_max_yaw_degrees = match_anomaly_max_yaw_degrees
        self.debug = debug
        self.connector = ROS2Connector(executor_type="multi_threaded")
        self.get_logger = self.connector.node.get_logger
        self.scene_manager = SceneManager(
            slots_file=slots_file,
            spawnables_file=spawnables_file,
            connector=self.connector,
        )

        self.vlm = vlm.with_structured_output(AnomalyDescription)
        self.n_seconds = n_seconds

        self.reported_anomalies: list[Anomaly] = list()
        wait_for_ros2_topics(self.connector, [self.camera_topic])
        # debug
        self.marker_array = MarkerArray()
        self.process_queue: Queue = Queue()
        self.last_processed = time.time()
        self.running = True
        self.vlm_thread = Thread(target=self.vlm_worker)

    def run(self):
        self.vlm_thread.start()
        while self.running:
            try:
                msg: Image = self.connector.receive_message(
                    self.camera_topic, timeout_sec=1.0
                ).payload
            except ValueError:
                self.get_logger().error(
                    f"Failed to receive a message from {self.camera_topic}"
                )
                continue
            img_stamp = rclpy.time.Time.from_msg(msg.header.stamp)
            image = CvBridge().imgmsg_to_cv2(  # type: ignore
                msg, desired_encoding="rgb8"
            )
            robot_location = self.get_robot_location()
            robot_location_stamp = rclpy.time.Time.from_msg(robot_location.header.stamp)

            try:
                _, candidate_pose = self.scene_manager.get_anomaly_box_pose(
                    robot_location.pose, [x.pose for x in self.reported_anomalies]
                )
            except ValueError:
                self.get_logger().debug("No candidate pose detected")
                candidate_pose = None

            if candidate_pose:
                self.get_logger().debug(f"Candidate pose: {candidate_pose}")

                b64_img = preprocess_image(image)
                task = InspectionTask(
                    b64_img, image, img_stamp, robot_location_stamp, candidate_pose
                )
                self.process_queue.put(task)

    def check_if_anomaly_is_reported(self, anomaly: Anomaly) -> bool:
        for reported_anomaly in self.reported_anomalies:
            if are_anomalies_close(
                reported_anomaly,
                anomaly,
                self.match_anomaly_max_distance,
                self.match_anomaly_max_yaw_degrees,
            ):
                return True
        return False

    def vlm_worker(self):
        self.last_processed = time.time()
        while self.running:
            try:
                task = self.process_queue.get(timeout=1)
                current = time.time()
                if current - self.last_processed < self.n_seconds:
                    continue

            except queue.Empty:
                continue

            ts = time.perf_counter()
            self.vlm_process(task)
            self.last_processed = time.time()
            self.get_logger().info(f"VLM analysis took: {time.perf_counter() - ts}")

    def vlm_process(self, task: InspectionTask):
        result: AnomalyDescription = self.detect_obstacle(task.b64_img)
        print("#############")
        self.get_logger().info(f"Result: {result.model_dump()}")
        print("#############")

        if result.anomaly_detected:
            message = Anomaly()
            message.pose = task.object_pose
            message.obstacle_type = result.obstacle_type
            message.anomaly_description = result.anomaly_description

            if self.check_if_anomaly_is_reported(message):
                self.get_logger().info(f"Anomaly already reported: {message}")
                return

            self.get_logger().info(f"Sending anomaly: {message}")
            if self.anomaly_images_dir:
                filename = save_image_to_disk(task.b64_img, self.anomaly_images_dir)
                message.filename = filename

            self.reported_anomalies.append(message)

            if self.debug:
                self._publish_marker(message)
            self.connector.send_message(
                ROS2Message(payload=message_to_ordereddict(message)),
                target=self.anomalies_topic,
                msg_type="robotec_kairos_ur10/msg/Anomaly",
            )

    def _publish_marker(self, message: Anomaly):
        # publish marker to Rviz 2
        marker = Marker()
        marker.header.frame_id = self.ego_target_frame
        marker.type = Marker.CUBE
        marker.id = len(self.marker_array.markers)
        marker.pose = message.pose
        marker.scale.x = 0.1
        marker.scale.y = 0.1
        marker.scale.z = 0.1
        marker.color.r = 1.0
        marker.color.g = 0.0
        marker.color.b = 0.0
        marker.color.a = 1.0
        self.marker_array.markers.append(marker)
        self.connector.send_message(
            ROS2Message(payload=message_to_ordereddict(self.marker_array)),
            target="/marker",
            msg_type="visualization_msgs/msg/MarkerArray",
        )

    def detect_obstacle(self, b64_img: str) -> AnomalyDescription:
        task = [
            SystemMessage(content=self.system_prompt),
            HumanMultimodalMessage(
                content=self.prompt,
                images=[b64_img],
            ),
        ]

        response = None
        for _ in range(3):
            try:
                response = cast(AnomalyDescription, self.vlm.invoke(task))
                break
            except OutputParserException as e:
                self.get_logger().error(f"Failed to set output parser: {e}")
        if response is None:
            raise Exception("Failed to set output parser")
        return response

    def get_robot_location(self) -> PoseStamped:
        transform = self.connector.get_transform(
            target_frame=self.ego_target_frame,
            source_frame=self.ego_source_frame,
            timeout_sec=1.0,
        )

        transform_time = rclpy.time.Time.from_msg(transform.header.stamp)
        current_time = self.connector._node.get_clock().now()

        age_seconds = (current_time - transform_time).nanoseconds / 1e9
        self.get_logger().debug(
            f"Got transform from {self.ego_source_frame} to {self.ego_target_frame} with age {age_seconds:.1f} seconds"
        )
        pose = PoseStamped()
        pose.header.frame_id = self.ego_target_frame
        pose.header.stamp = transform.header.stamp
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        return pose

    def stop(self):
        self.running = False
        self.vlm_thread.join()


@ROS2Context()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slots-file", type=str, default="scripts/resources/slots.csv")
    parser.add_argument(
        "--spawnables-file", type=str, default="scripts/resources/spawnables.csv"
    )
    parser.add_argument("--vlm-vendor", type=str, default="ollama")
    parser.add_argument("--vlm-model", type=str, default="gemma3:27b")
    parser.add_argument(
        "--vlm-base_url",
        type=str,
    )
    parser.add_argument(
        "--camera-topic", type=str, default="/rgbd_camera/camera_image_color"
    )
    parser.add_argument("--ego-source-frame", type=str, default="egobase_footprint")
    parser.add_argument("--ego-target-frame", type=str, default="odom")
    parser.add_argument("--no-images-saving", action="store_true")
    parser.add_argument("--anomaly-images-dir", type=str, default="./anomaly_images")
    parser.add_argument("--anomalies-topic", type=str, default="/inspection_result")
    parser.add_argument("--n-seconds", type=int, default=5)
    args = parser.parse_args()
    vlm = get_model(
        model=args.vlm_model, vendor=args.vlm_vendor, base_url=args.vlm_base_url
    )

    inspector = VlmWarehouseInspector(
        vlm=vlm,
        slots_file=args.slots_file,
        spawnables_file=args.spawnables_file,
        camera_topic=args.camera_topic,
        ego_target_frame=args.ego_target_frame,
        ego_source_frame=args.ego_source_frame,
        anomaly_images_dir=(
            args.anomaly_images_dir if not args.no_images_saving else None
        ),
        anomalies_topic=args.anomalies_topic,
        n_seconds=args.n_seconds,
    )

    inspector.run()


if __name__ == "__main__":
    main()
