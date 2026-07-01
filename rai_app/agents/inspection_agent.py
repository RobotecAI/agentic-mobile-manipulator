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
import openai
import rclpy
import rclpy.time
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
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
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from robotec_kairos_ur10.msg import Anomaly
from rosidl_runtime_py import message_to_ordereddict
from sensor_msgs.msg import Image
from tf2_ros import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray

from rai_app.agents.vlm_transport import publish_vlm_description
from rai_app.config.vlm_inspection_prompts import (
    INSPECTION_JSON_SYSTEM_PROMPT,
    INSPECTION_JSON_USER_PROMPT,
    INSPECTION_TEXT_FINAL_SYSTEM_PROMPT,
    INSPECTION_TEXT_FINAL_USER_PROMPT,
    INSPECTION_TEXT_SYSTEM_PROMPT,
    INSPECTION_TEXT_USER_PROMPT,
    InspectionOutput,
)
from rai_app.environment import SceneManager
from rai_app.geometry_helpers import get_yaw_difference
from rai_app.initialization.llms import get_vlm_backend, get_vlm_model
from rai_app.initialization.structured import vlm_structured


class AnomalyDescription(BaseModel):
    obstacle_type: Literal["box", "trash", "nothing", "other"] = Field(
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

    return bool(position_ok and orientation_ok)


def are_anomalies_close(
    anomaly1: Anomaly, anomaly2: Anomaly, distance: float, rot_degrees: float
) -> bool:
    # NOTE (jmatejcz) model can detect same thing as different types so I think
    # connecting this match out is a good idea
    # obstacle_type_match = anomaly1.obstacle_type == anomaly2.obstacle_type
    poses_match = are_poses_close(anomaly1.pose, anomaly2.pose, distance, rot_degrees)
    return poses_match


@dataclass
class InspectionTask:
    b64_img: str
    image: np.ndarray
    img_stamp: rclpy.time.Time
    robot_location_stamp: rclpy.time.Time
    object_pose: Pose | None


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
        match_anomaly_max_distance: float = 1.0,
        match_anomaly_max_yaw_degrees: float = 50.0,
        n_seconds: int = 1,
        debug: bool = True,
        vlm_backend: str | None = None,
    ):
        self.camera_topic = camera_topic
        self.ego_target_frame = ego_target_frame
        self.ego_source_frame = ego_source_frame
        self.anomaly_images_dir = anomaly_images_dir
        self.anomalies_topic = anomalies_topic
        self.anomalies_type = "robotec_kairos_ur10/msg/Anomaly"
        self.qos_profile = QoSProfile(
            depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
        )
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

        self.vlm = vlm
        self.vlm_backend = vlm_backend
        self.n_seconds = n_seconds

        self.reported_anomalies: list[tuple[Anomaly, float]] = list()
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
                    self.camera_topic, timeout_sec=3.0
                ).payload
            except (ValueError, TimeoutError):
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
                    robot_location.pose, [x[0].pose for x in self.reported_anomalies]
                )
            except ValueError:
                self.get_logger().debug("No candidate pose detected")
                candidate_pose = None
            self.get_logger().debug(f"Candidate pose: {candidate_pose}")

            b64_img = preprocess_image(image)
            task = InspectionTask(
                b64_img, image, img_stamp, robot_location_stamp, candidate_pose
            )
            self.process_queue.put(task)

    def check_if_anomaly_is_reported(self, anomaly: Anomaly) -> bool:
        # Remove anomalies older than 1 minute
        old_anomalies = len(self.reported_anomalies)
        now = time.time()
        self.reported_anomalies = [
            (anomaly, timestamp)
            for anomaly, timestamp in self.reported_anomalies
            if now - timestamp < 60
        ]
        if old_anomalies > 0:
            self.get_logger().info(
                f"Actual anomalies: {len(self.reported_anomalies) / old_anomalies}"
            )

        for reported_anomaly, _ in self.reported_anomalies:
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

    def _prepare_description(self, anomaly: Anomaly) -> str:
        return f"Anomaly detected: {anomaly.obstacle_type} at ({anomaly.pose.position.x}, {anomaly.pose.position.y}, {anomaly.pose.position.z}). Description: {anomaly.anomaly_description}"

    def vlm_process(self, task: InspectionTask, n_retries=3):
        result: AnomalyDescription | None = None
        for _ in range(n_retries):
            try:
                result, inspection_results, description = self.detect_obstacle(
                    task.b64_img
                )
                break
            except openai.APIConnectionError:
                self.get_logger().warning("Connection error")

        if result is None:
            return

        print("#############")
        self.get_logger().info(f"Result: {result.model_dump()}")
        print("#############")

        if result.obstacle_type in [
            "box",
            "trash",
            "other",
        ]:
            if result.obstacle_type != "other" and task.object_pose is None:
                self.get_logger().error(
                    "Agent detected anomaly, but no object pose was been discovered"
                    "by th GT detection module. Skipping {result.obstacle_type}:"
                    f"{result.anomaly_description}..."
                )
                result.obstacle_type = "other"

            message = Anomaly()
            if result.obstacle_type == "other":
                message.pose = self.get_robot_location().pose
            else:
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

            now = time.time()
            self.reported_anomalies.append((message, now))

            if self.debug:
                self._publish_marker(message)

            self.connector.send_message(
                ROS2Message(payload=message_to_ordereddict(message)),
                target=self.anomalies_topic,
                msg_type=self.anomalies_type,
                qos_profile=self.qos_profile,
            )

            cv2_image = CvBridge().cv2_to_imgmsg(task.image, encoding="passthrough")
            cv2_image.encoding = "rgb8"

            if message.obstacle_type == "other":
                info = "Anomaly of type 'other' detected.\nNo action can be taken by the robot, please investigate manually"
            elif message.obstacle_type == "box":
                info = "Box detected, submitted task to move it to the inspection area"
            elif message.obstacle_type == "trash":
                info = (
                    "Trash detected, submitted task to throw it out to the garbage bin"
                )
            else:
                info = "Unknown anomaly type"

            if "orderly" not in str(message.anomaly_description).lower():
                vlm_description = f"{info}.\nDetails: {message.anomaly_description}"
            else:
                vlm_description = info

            publish_vlm_description(
                self.connector,
                cv2_image,
                vlm_description,
                "Inspection",
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
            SystemMessage(content=INSPECTION_TEXT_SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content=INSPECTION_TEXT_USER_PROMPT,
                images=[b64_img],
            ),
        ]

        # First get the descriptive analysis
        descriptive_response = self.vlm.invoke(task)
        self.get_logger().info(f"Descriptive response: {descriptive_response.content}")

        structured_task = [
            SystemMessage(content=INSPECTION_JSON_SYSTEM_PROMPT),
            HumanMultimodalMessage(
                content=INSPECTION_JSON_USER_PROMPT.format(
                    descriptive_response=descriptive_response.content
                ),
            ),
        ]

        llm_structured = vlm_structured(self.vlm, InspectionOutput, self.vlm_backend)
        response: InspectionOutput = llm_structured.invoke(structured_task)
        self.get_logger().info(f"Inspection output: {response}")
        inspection_results = response.inspection_results

        if len(response.inspection_results) > 0:
            final_task = [
                SystemMessage(INSPECTION_TEXT_FINAL_SYSTEM_PROMPT),
                HumanMessage(
                    content=INSPECTION_TEXT_FINAL_USER_PROMPT.format(
                        anomalies="\n".join(response.inspection_results)
                    )
                ),
            ]
            response = cast(
                AnomalyDescription,
                vlm_structured(self.vlm, AnomalyDescription, self.vlm_backend).invoke(
                    final_task
                ),
            )
        else:
            response = AnomalyDescription(
                anomaly_detected=False, anomaly_description="", obstacle_type="nothing"
            )
        return response, inspection_results, descriptive_response.content

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
    vlm = get_vlm_model(config_name="inspection_agent")

    inspector = VlmWarehouseInspector(
        vlm=vlm,
        vlm_backend=get_vlm_backend(config_name="inspection_agent"),
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
