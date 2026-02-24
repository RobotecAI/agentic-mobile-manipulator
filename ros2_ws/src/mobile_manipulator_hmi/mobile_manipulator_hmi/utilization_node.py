#!/usr/bin/env python3
import re
import subprocess
from typing import Dict, Optional

import rclpy
from demo_msgs.msg import Utilization
from lifecycle_msgs.srv import GetState
from psutil import cpu_percent, virtual_memory
from rclpy.executors import MultiThreadedExecutor
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node


class UtilizationCollector:
    """Collects CPU, RAM, GPU, and NPU utilization."""

    def __init__(
        self,
        logger: RcutilsLogger,
        include_gpu: bool = False,
        include_npu: bool = False,
    ):
        self.include_gpu = include_gpu
        self.include_npu = include_npu
        self.logger = logger

    def collect(self) -> Dict[str, float]:
        utilization: Dict[str, float] = {}
        try:
            utilization["cpu"] = self._cpu()
        except Exception as e:
            utilization["cpu"] = -1.0
            self.logger.error(f"CPU collection failed: {e}")

        try:
            utilization["ram"] = self._ram()
        except Exception as e:
            utilization["ram"] = -1.0
            self.logger.error(f"RAM collection failed: {e}")

        if self.include_gpu:
            try:
                val = self._gpu()
                utilization["gpu"] = val if val is not None else -1.0
            except Exception as e:
                utilization["gpu"] = -1.0
                self.logger.error(f"GPU collection failed: {e}")

        if self.include_npu:
            try:
                val = self._npu()
                utilization["npu"] = val if val is not None else -1.0
            except Exception as e:
                utilization["npu"] = -1.0
                self.logger.error(f"NPU collection failed: {e}")

        return utilization

    @staticmethod
    def _cpu(interval: int = 0) -> float:
        return cpu_percent(interval=interval)

    @staticmethod
    def _ram() -> float:
        return virtual_memory().percent

    @staticmethod
    def _gpu() -> Optional[float]:
        # Try AMD
        try:
            result = subprocess.check_output(["rocm-smi", "--showuse"], text=True)
            match = re.search(r"GPU use \(%\):\s+(\d+)", result)
            return int(match.group(1)) if match else None
        except FileNotFoundError:
            pass

        # Try NVIDIA
        try:
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
                text=True,
            )
            return float(result.strip().rstrip("%"))
        except FileNotFoundError:
            pass
        return None


    @staticmethod
    def _npu() -> Optional[float]:
        # Placeholder for NPU
        return None


class UtilizationPublisher(Node):
    """ROS2 node publishing system utilization and Nav2/MoveIt2 states."""

    def __init__(
        self,
        include_gpu: bool = False,
        include_npu: bool = False,
        publish_interval: float = 5.0,
        nav2_node_name: str = "/bt_navigator",
    ):
        super().__init__("utilization_publisher")
        self._publisher = self.create_publisher(Utilization, "utilization", 10)
        self._collector = UtilizationCollector(
            include_gpu=include_gpu, include_npu=include_npu, logger=self.get_logger()
        )

        # Lifecycle service clients
        self._nav2_client = self.create_client(GetState, f"{nav2_node_name}/get_state")

        # States
        self.nav2_state = False
        self.moveit2_state = False

        # Timers
        self.create_timer(publish_interval, self._on_timer)
        self.create_timer(2.0, self._check_nav2_state)
        self.create_timer(2.0, self._check_moveit2_state)

        self.get_logger().info(
            f"UtilizationPublisher initialized (GPU={include_gpu}, NPU={include_npu}, interval={publish_interval}s)"
        )

    def _check_nav2_state(self):
        if not self._nav2_client.service_is_ready():
            self.get_logger().warn("Nav2 service not ready")
            return
        req = GetState.Request()
        future = self._nav2_client.call_async(req)
        future.add_done_callback(self._nav2_state_callback)

    def _nav2_state_callback(self, future):
        try:
            res = future.result()
            self.nav2_state = res.current_state.id == 3
            self.get_logger().debug(f"Nav2 active={self.nav2_state}")
        except Exception as e:
            self.get_logger().error(f"Failed to get Nav2 state: {e}")
            self.nav2_state = False

    def _check_moveit2_state(self):
        node_list = self.get_node_names()
        if "move_group" in node_list:
            self.moveit2_state = True
        else:
            self.moveit2_state = False

    def _on_timer(self):
        utilization = self._collector.collect()
        msg = Utilization()
        msg.component_names = list(utilization.keys())
        msg.component_values = list(utilization.values())
        msg.nav2_state = self.nav2_state
        msg.moveit2_state = self.moveit2_state

        self._publisher.publish(msg)
        self.get_logger().info(
            f"Published utilization: "
            f"{', '.join(f'{k}={v:.1f}%' for k, v in utilization.items())}, "
            f"Nav2 active={self.nav2_state}, MoveIt2 active={self.moveit2_state}"
        )


def main():
    rclpy.init()
    try:
        node = UtilizationPublisher(include_gpu=True, include_npu=True)
        executor = MultiThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
