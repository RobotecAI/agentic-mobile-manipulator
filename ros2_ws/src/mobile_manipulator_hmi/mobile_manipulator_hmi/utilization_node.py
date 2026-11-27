#!/usr/bin/env python3
import ctypes
import fcntl
import glob
import os
import re
import shutil
import struct
import subprocess
import threading
import time
from typing import Dict, Optional

import rclpy
from demo_msgs.msg import Utilization
from lifecycle_msgs.srv import GetState
from psutil import cpu_percent, virtual_memory
from rclpy.executors import MultiThreadedExecutor
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.node import Node


def find_tool(name: str) -> Optional[str]:
    """Path of a ROCm tool: on PATH, else under /opt/rocm*/bin (ROCm installs there)."""
    found = shutil.which(name)
    if found:
        return found
    candidates = sorted(glob.glob(f"/opt/rocm*/bin/{name}") + glob.glob(f"/opt/rocm*/*/bin/{name}"))
    return candidates[-1] if candidates else None


class NpuActivity:
    """Best-effort NPU busy estimate for AMD Ryzen AI NPUs (amdxdna driver).

    The driver reports no utilization %, but every hardware context counts its
    completed commands. A thread samples the counters every SAMPLE_S; busy % is the
    share of samples since the last read in which any counter moved. Uses
    GET_ARRAY(HW_CONTEXT_ALL) and falls back to the older GET_INFO(QUERY_HW_CONTEXTS);
    any device or driver without either is reported as "not available".
    """

    SAMPLE_S = 0.2
    # uapi drm/amdxdna_accel.h. In both entry structs command_completions is the u64 at offset 32.
    GET_INFO = (3 << 30) | (16 << 16) | (ord("d") << 8) | (0x40 + 7)
    GET_ARRAY = (3 << 30) | (24 << 16) | (ord("d") << 8) | (0x40 + 10)
    QUERY_HW_CONTEXTS = 5
    ARRAY_ENTRY_SIZE = 144  # struct amdxdna_drm_hwctx_entry
    INFO_ENTRY_SIZE = 56  # struct amdxdna_drm_query_hwctx
    MAX_ENTRIES = 64

    def __init__(self):
        devices = sorted(glob.glob("/dev/accel/accel*"))
        if not devices:
            raise OSError("no /dev/accel device")
        self.fd = None
        error: Optional[OSError] = None
        for path in devices:
            fd = None
            try:
                fd = os.open(path, os.O_RDWR)
                for query in (self._from_array, self._from_info):
                    try:
                        query(fd)
                        self.fd, self.query = fd, query
                        break
                    except OSError as e:
                        error = e
                if self.fd is not None:
                    break
                os.close(fd)
            except OSError as e:
                error = e
        if self.fd is None:
            raise OSError(f"no amdxdna NPU answered ({error})")
        self.lock = threading.Lock()
        self.samples = 0
        self.busy = 0
        threading.Thread(target=self._sample, daemon=True).start()

    def _from_array(self, fd: int) -> int:
        buf = ctypes.create_string_buffer(self.ARRAY_ENTRY_SIZE * self.MAX_ENTRIES)
        req = bytearray(struct.pack("IIIIQ", 0, self.ARRAY_ENTRY_SIZE, self.MAX_ENTRIES, 0, ctypes.addressof(buf)))
        fcntl.ioctl(fd, self.GET_ARRAY, req)
        _, size, count, _, _ = struct.unpack("IIIIQ", req)
        return sum(struct.unpack_from("Q", buf.raw, i * size + 32)[0] for i in range(min(count, self.MAX_ENTRIES)))

    def _from_info(self, fd: int) -> int:
        buf = ctypes.create_string_buffer(self.INFO_ENTRY_SIZE * self.MAX_ENTRIES)
        req = bytearray(struct.pack("IIQ", self.QUERY_HW_CONTEXTS, len(buf), ctypes.addressof(buf)))
        fcntl.ioctl(fd, self.GET_INFO, req)
        count = struct.unpack("IIQ", req)[1] // self.INFO_ENTRY_SIZE
        return sum(struct.unpack_from("Q", buf.raw, i * self.INFO_ENTRY_SIZE + 32)[0] for i in range(count))

    def completions(self) -> int:
        """Sum of command completions over all hardware contexts."""
        return self.query(self.fd)

    def _sample(self):
        last = self.completions()
        while True:
            time.sleep(self.SAMPLE_S)
            try:
                now = self.completions()
            except OSError:
                continue
            with self.lock:
                self.samples += 1
                self.busy += now != last
            last = now

    def read(self) -> Optional[float]:
        with self.lock:
            if not self.samples:
                return None
            value = 100.0 * self.busy / self.samples
            self.samples = self.busy = 0
        return value


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
        self.npu: Optional[NpuActivity] = None
        if include_npu:
            try:
                self.npu = NpuActivity()
            except OSError as e:
                logger.warn(f"NPU usage will not be reported: {e} (is the user in the render group?)")

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
        """GPU load in % from rocm-smi, else amd-smi; None if neither is installed."""
        try:
            result = subprocess.check_output([find_tool("rocm-smi") or "rocm-smi", "--showuse"], text=True)
            match = re.search(r"GPU use \(%\):\s+(\d+)", result)
            if match:
                return float(match.group(1))
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        try:
            result = subprocess.check_output(
                [find_tool("amd-smi") or "amd-smi", "metric", "--usage", "--json"], text=True
            )
            # "gfx_activity" is a number or {"value": n, "unit": "%"} depending on the version.
            values = [
                float(m)
                for m in re.findall(r'"gfx_activity":\s*(?:\{\s*"value":\s*)?"?(\d+(?:\.\d+)?)', result)
            ]
            if values:
                return max(values)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        return None


    def _npu(self) -> Optional[float]:
        return self.npu.read() if self.npu else None


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

        if include_gpu and not (find_tool("rocm-smi") or find_tool("amd-smi")):
            self.get_logger().warn(
                "Neither rocm-smi nor amd-smi is installed: GPU usage will not be reported. "
                "Install amd-smi (AMD ROCm apt repository) to see it in the HMI."
            )
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
