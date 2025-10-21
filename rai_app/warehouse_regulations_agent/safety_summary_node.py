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

#!/usr/bin/env python3
"""
ROS2 node for generating safety violation summaries.
This node periodically loads violation data from a JSON file and provides
a service to generate executive summaries of safety violations.
"""

import argparse
import json
import time
from pathlib import Path

import rclpy
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from rai.communication.ros2 import ROS2Context
from rclpy.node import Node
from std_srvs.srv import Trigger

from rai_app.warehouse_regulations_agent.violation_storage import ViolationStorage


class SafetySummaryNode(Node):
    """ROS2 node for generating safety violation summaries."""

    def __init__(
        self,
        violations_file: str = "safety_violations.json",
        llm_model: str = "LFM2-VL-3B-preview-251009-0235-2258",
        llm_base_url: str = "http://localhost:8084",
        reload_interval: float = 2.0,
    ):
        """
        Initialize the safety summary node.

        Args:
            violations_file: Path to the JSON file containing violation data
            llm_model: Language model identifier for summary generation
            llm_base_url: Base URL for the LLM endpoint
            reload_interval: Interval in seconds to reload violation data
        """
        super().__init__("safety_summary_node")
        self.violations_file = violations_file
        self.reload_interval = reload_interval
        self.last_reload_time = 0.0

        # Initialize violation storage
        self.violation_storage = ViolationStorage(violations_file)

        # Initialize LLM for summary generation
        self.llm: BaseChatModel = ChatOpenAI(model=llm_model, base_url=llm_base_url)

        # Initialize ROS2 context
        self.logger = self.get_logger()

        # Create service for generating summaries
        self.summary_service = self.create_service(
            srv_type=Trigger,
            srv_name="/safety/generate_anomaly_summary",
            callback=self.generate_anomaly_summary,
        )

        # Create timer for periodic data reload
        self.reload_timer = self.create_timer(
            timer_period_sec=reload_interval,
            callback=self.reload_violation_data,
        )

        self.logger.info(
            f"SafetySummaryNode initialized with violations file: {violations_file}"
        )
        self.logger.info(f"Reload interval: {reload_interval} seconds")

        # Initial data load
        self.reload_violation_data()

    def reload_violation_data(self):
        """Reload violation data from the JSON file."""
        try:
            if Path(self.violations_file).exists():
                self.violation_storage = ViolationStorage(self.violations_file)
                self.last_reload_time = time.time()
                self.logger.info(f"Reloaded violation data from {self.violations_file}")
            else:
                self.logger.warn(f"Violations file {self.violations_file} not found")
        except Exception as e:
            self.logger.error(f"Error reloading violation data: {e}")

    def generate_anomaly_summary(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """
        Generate an executive summary of safety anomalies using LLM.

        Args:
            request: Trigger request (no parameters needed)
            response: Trigger response containing the summary

        Returns:
            Trigger response with success status and summary message
        """
        try:
            self.logger.info("Generating safety anomaly summary...")

            # Get violation statistics and recent violations
            stats = self.violation_storage.get_violation_statistics()
            recent_violations = self.violation_storage.get_recent_violations(20)
            if not recent_violations:
                response.success = True
                response.message = (
                    "No safety violations detected in the system. "
                    "All safety protocols are being followed correctly."
                )
                return response

            # Prepare data for LLM analysis
            violation_data = {
                "statistics": stats,
                "recent_violations": recent_violations,
                "total_violations": len(self.violation_storage.violations_history),
            }

            # Create prompt for executive summary
            summary_prompt = f"""
            As a safety compliance expert, analyze the following warehouse safety violation data and generate an executive summary.

            Safety Violation Data:
            {json.dumps(violation_data, indent=2)}

            Please provide:
            1. Executive Summary (2-3 sentences highlighting key safety concerns)
            2. List OSHA regulations IDs that are violated. Only IDs, no text.

            Format your response as a structured executive report suitable for management review.
            Focus on compliance, risk mitigation, and operational improvements.
            """

            # Generate summary using LLM
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(
                    content=(
                        "You are a safety compliance expert providing executive summaries "
                        "for warehouse safety violations. Be concise, professional, and actionable."
                    )
                ),
                HumanMessage(content=summary_prompt),
            ]

            llm_response = self.llm.invoke(messages)
            summary = (
                llm_response.content
                if hasattr(llm_response, "content")
                else str(llm_response)
            )

            # Format the response
            response.success = True
            response.message = (
                f"SAFETY ANOMALY EXECUTIVE SUMMARY\n"
                f"{'=' * 50}\n\n"
                f"{summary}\n\n"
                f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            self.logger.info("Safety anomaly summary generated successfully")

        except Exception as e:
            self.logger.error(f"Error generating safety anomaly summary: {e}")
            response.success = False
            response.message = f"Failed to generate summary: {str(e)}"

        return response


@ROS2Context()
def main():
    """Main function to run the safety summary node."""
    parser = argparse.ArgumentParser(description="Run safety summary node")
    parser.add_argument(
        "--violations-file",
        type=str,
        default="safety_violations.json",
        help="Path to the JSON file containing violation data",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="LFM2-VL-3B-preview-251009-0235-2258",
        help="Language model identifier for summary generation",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default="http://localhost:8084",
        help="Base URL for the LLM endpoint",
    )
    parser.add_argument(
        "--reload-interval",
        type=float,
        default=15.0,
        help="Interval in seconds to reload violation data",
    )

    args = parser.parse_args()

    node = SafetySummaryNode(
        violations_file=args.violations_file,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        reload_interval=args.reload_interval,
    )
    rclpy.spin(node)


if __name__ == "__main__":
    main()
