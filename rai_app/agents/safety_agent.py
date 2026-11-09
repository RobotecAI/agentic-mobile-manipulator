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
import json
import time
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from langchain_core.language_models import BaseChatModel
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_topics,
)
from rai.messages import HumanMultimodalMessage, preprocess_image
from sensor_msgs.msg import Image
from skimage.metrics import structural_similarity as ssim

from rai_app.agents.vlm_transport import publish_vlm_description
from rai_app.initialization.llms import (
    get_embeddings_model,
    get_reranker_model_url,
    get_vlm_model,
)

# Reuse vector store loader and regulation agent factory from the warehouse regulations module
from rai_app.warehouse_regulations_agent.rag import load_vector_store  # type: ignore
from rai_app.warehouse_regulations_agent.violation_storage import ViolationStorage
from rai_app.warehouse_regulations_agent.warehouse_safety_agent import (
    create_image_regulation_agent,  # type: ignore
)


def are_2_images_similar(
    image1: np.ndarray, image2: np.ndarray, threshold: float = 0.95
) -> bool:
    """
    Use SSIM (Structural Similarity Index) via OpenCV to assess similarity between two images.
    Threshold is the minimum similarity for images to be considered similar (default: 0.95).
    """
    # Convert both images to grayscale for comparison
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY) if image1.ndim == 3 else image1
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY) if image2.ndim == 3 else image2

    # Resize images to match (if not already the same shape)
    if gray1.shape != gray2.shape:
        min_h = min(gray1.shape[0], gray2.shape[0])
        min_w = min(gray1.shape[1], gray2.shape[1])
        gray1 = cv2.resize(gray1, (min_w, min_h))
        gray2 = cv2.resize(gray2, (min_w, min_h))

    # Compute structural similarity index
    # SSIM is available in skimage; if unavailable, fallback to mean absolute error
    try:
        score, _ = ssim(gray1, gray2, full=True)
        return score >= threshold
    except ImportError:
        # Fallback: mean absolute error
        mae = np.mean(np.abs(gray1.astype("float") - gray2.astype("float")))
        return mae < (1.0 - threshold) * 255


class SafetyAgent:
    def __init__(
        self,
        vector_db: str,
        camera_topic: str = "/rgbd_camera/camera_image_color",
        safety_topic: str = "/safety",
        k: int = 3,
        n_seconds: int = 5,
        violations_file: str = "safety_violations.json",
    ):
        self.connector = ROS2Connector(executor_type="multi_threaded")
        self.get_logger = self.connector.node.get_logger
        self.camera_topic = camera_topic
        self.safety_topic = safety_topic
        self.k = k
        self.n_seconds = n_seconds
        self.last_processed: float = 0.0

        # Initialize violation storage
        self.violation_storage = ViolationStorage(violations_file)

        # Load vector store once
        embedding_model = get_embeddings_model("safety_agent")
        self.vector_store = load_vector_store(embedding_model, vector_db)

        self.reranker_url = get_reranker_model_url("safety_agent")

        # Vision-language model (served via REST compatible with ChatOpenAI client)
        self.vlm: BaseChatModel = get_vlm_model(config_name="safety_agent")

        # Use same model as LLM for final assessment
        self.llm: BaseChatModel = self.vlm

        # Build the regulation agent once
        self.agent = create_image_regulation_agent(
            vlm=self.vlm,
            llm=self.llm,
            vector_store=self.vector_store,
            reranker_url=self.reranker_url,
            k=self.k,
        )

        # Ensure the camera topic is available before running
        wait_for_ros2_topics(self.connector, [self.camera_topic])

        self.processed_cnt = 0
        self.prev_image = None

    def get_violations_summary(self):
        """Return a textual summary of all stored violations."""
        return self.violation_storage.get_violations_summary()

    def get_violations_by_type(self, violation_type: str):
        """Return violations filtered by type."""
        return self.violation_storage.get_violations_by_type(violation_type)

    def get_recent_violations(self, n: int = 10):
        """Return the ``n`` most recent violations."""
        return self.violation_storage.get_recent_violations(n)

    def clear_violations(self) -> None:
        """Delete all stored violations and emit a log entry."""
        self.violation_storage.clear_violations()
        self.get_logger().info("All violations cleared")

    def run(self):
        self.get_logger().info("SafetyAgent started; waiting for images...")
        while rclpy.ok():
            try:
                msg = self.connector.receive_message(
                    self.camera_topic, timeout_sec=5.0, msg_type="sensor_msgs/msg/Image"
                )
                image = CvBridge().imgmsg_to_cv2(  # type: ignore
                    msg.payload, desired_encoding="rgb8"
                )
                # Save the received image as a PNG file for later reference
                Path("safety_agent_images").mkdir(parents=True, exist_ok=True)
                if self.prev_image is not None:
                    if are_2_images_similar(self.prev_image, image):
                        self.get_logger().info("Images are similar, skipping")
                        time.sleep(5)
                        continue
                self.prev_image = image
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(
                    f"safety_agent_images/image{self.processed_cnt}.png", image_bgr
                )
                b64_img = preprocess_image(image)
                self.processed_cnt += 1
            except (ValueError, TimeoutError):
                # No image available yet
                continue

            now = time.time()
            if now - self.last_processed < self.n_seconds:
                continue

            self.last_processed = now
            self._process_image(b64_img)

    def _build_ros2_image(self, b64_img: str) -> Image:
        cv2_image = cv2.imdecode(
            np.frombuffer(base64.b64decode(b64_img), np.uint8), cv2.IMREAD_COLOR
        )
        image_bgr = cv2.cvtColor(cv2_image, cv2.COLOR_RGB2BGR)
        ros2_image = CvBridge().cv2_to_imgmsg(image_bgr, encoding="passthrough")
        ros2_image.encoding = "rgb8"
        return ros2_image

    def _process_image(self, b64_img: str) -> None:
        ts = time.perf_counter()
        state = self.agent.invoke(
            {
                "messages": [
                    HumanMultimodalMessage(
                        content="",
                        images=[b64_img],
                    )
                ]
            }
        )

        output = state.get("output") if isinstance(state, dict) else state
        ts = time.perf_counter() - ts
        print(f"Agent took {ts} seconds")
        print(f"Output: {output}")
        violations: list[dict[str, Any]] = []
        if isinstance(output, list):
            # Agent returns a list of Pydantic models or dicts
            for v in output:
                if hasattr(v, "model_dump"):
                    violations.append(cast(dict[str, Any], v.model_dump()))
                elif isinstance(v, dict):
                    violations.append(v)

        if not violations:
            # No safety issues detected: do nothing
            self.get_logger().info("No safety violations detected.")
            return

        # Store violations in memory and persist to file
        self.violation_storage.store_violations(violations)
        new_violations = []
        for violation in violations:
            if (
                "applicable_regulations" not in violation
                or len(violation["applicable_regulations"]) == 0
            ):
                self.get_logger().info(
                    f"Violation {violation['hazard']} is not applicable to any regulation - skipping"
                )
                continue
            new_violations.append(violation)
        violations = new_violations
        agent_str_output = ""
        for violation in violations:
            agent_str_output += f"Hazard: {violation['hazard']}\n"
            agent_str_output += f"Severity: {violation['severity']}\n"
            agent_str_output += f"Rationale: {violation['rationale']}\n"
            agent_str_output += "Applicable Regulations:\n:"
            if (
                "applicable_regulations" not in violation
                or len(violation["applicable_regulations"]) == 0
            ):
                continue
            else:
                for regulation in violation["applicable_regulations"]:
                    agent_str_output += (
                        f" - {regulation['regulation_number']}: {regulation['excerpt']}"
                    )
            agent_str_output += "\n"

        self.get_logger().info(agent_str_output)

        # Publish violations to /safety as JSON string
        payload = json.dumps({"violations": violations}, ensure_ascii=False)
        print(f"Payload: {payload}")
        self.connector.send_message(
            ROS2Message(payload={"data": payload}),
            target=self.safety_topic,
            msg_type="std_msgs/msg/String",
        )
        ros2_image = self._build_ros2_image(b64_img)
        publish_vlm_description(self.connector, ros2_image, agent_str_output, "Safety")
        self.get_logger().info(
            f"Published {len(violations)} safety violation(s) to {self.safety_topic} and stored in history"
        )


@ROS2Context()
def main():
    parser = argparse.ArgumentParser(description="Run online safety agent")
    parser.add_argument("--vector-db", required=True, help="Path to FAISS vector DB")
    parser.add_argument(
        "--camera-topic",
        type=str,
        default="/rgbd_camera/camera_image_color",
        help="Camera topic to subscribe to",
    )
    parser.add_argument(
        "--safety-topic",
        type=str,
        default="/safety",
        help="Topic to publish safety violations to",
    )
    parser.add_argument("-k", type=int, default=10, help="RAG top-k retrieval")
    parser.add_argument(
        "--n-seconds",
        type=int,
        default=5,
        help="Minimum seconds between consecutive analyses",
    )
    parser.add_argument(
        "--violations-file",
        type=str,
        default="safety_violations.json",
        help="File to store violations history",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print violations summary and exit",
    )

    args = parser.parse_args()

    agent = SafetyAgent(
        vector_db=args.vector_db,
        camera_topic=args.camera_topic,
        safety_topic=args.safety_topic,
        k=args.k,
        n_seconds=args.n_seconds,
        violations_file=args.violations_file,
    )

    if args.print_summary:
        summary = agent.get_violations_summary()
        print("Safety Violations Summary")
        print("=" * 50)
        print(f"Total violations: {summary['total_violations']}")
        print("Violations by type:")
        for violation_type, count in summary["violations_by_type"].items():
            print(f"  {violation_type}: {count}")
        print(f"Last updated: {summary['last_updated']}")
        if summary["recent_violations"]:
            print("\nRecent violations (last 10):")
            for violation in summary["recent_violations"]:
                print(
                    f"  {violation['timestamp']}: {violation['violation'].get('type', 'unknown')}"
                )
        return

    agent.run()


if __name__ == "__main__":
    main()
