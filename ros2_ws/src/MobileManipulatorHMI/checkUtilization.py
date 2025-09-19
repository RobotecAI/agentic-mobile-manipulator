#!/usr/bin/env python3
# cpu_gpu_ram_publisher.py
# Publishes CPU, RAM and GPU utilization as std_msgs/Float32MultiArray
# Usage: source ROS2, then: python3 cpu_gpu_ram_publisher.py

import subprocess
import shlex
import time
from typing import List

import psutil
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

# Optional: try GPUtil if available (more portable for multiple vendors)
try:
    import GPUtil
    HAVE_GPUTIL = True
except Exception:
    HAVE_GPUTIL = False


def get_gpu_util_nvidia() -> List[float]:
    """
    Query nvidia-smi to return list of GPU utilization percentages (0..100).
    Returns empty list if no nvidia-smi or no GPUs.
    """
    try:
        cmd = "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits"
        proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=1.0)
        if proc.returncode != 0:
            return []
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return [float(x) for x in lines]
    except Exception:
        return []


def get_gpu_util_gputil() -> List[float]:
    """Use GPUtil if available. Returns list of GPU loads in percent or empty list."""
    if not HAVE_GPUTIL:
        return []
    try:
        gpus = GPUtil.getGPUs()
        return [gpu.load * 100.0 for gpu in gpus]
    except Exception:
        return []


def get_gpu_utils() -> List[float]:
    """Try multiple methods, returning first successful list or [] if none."""
    # Prefer GPUtil if available (handles many drivers), else try nvidia-smi
    out = get_gpu_util_gputil()
    if out:
        return out
    return get_gpu_util_nvidia()


class UtilPublisher(Node):
    def __init__(self, topic_name='system_util', publish_hz: float = 1.0):
        super().__init__('system_util_publisher')
        self.pub = self.create_publisher(Float32MultiArray, topic_name, 10)
        self.timer_period = 1.0 / publish_hz
        # warm-up cpu_percent measurement
        psutil.cpu_percent(interval=None)
        self.get_logger().info(f'Publishing system utilization to "{topic_name}" at {publish_hz} Hz')
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

    def timer_callback(self):
        # CPU: short interval to get recent snapshot (non-blocking if small)
        try:
            cpu = psutil.cpu_percent(interval=0.05)  # small block to get meaningful value
        except Exception:
            cpu = 0.0

        # RAM: percentage used
        try:
            mem = psutil.virtual_memory()
            ram = float(mem.percent)
        except Exception:
            ram = 0.0

        # GPU(s)
        gpus = get_gpu_utils()  # list of floats
        # Build payload: cpu, ram, then per-gpu
        payload = [float(cpu), float(ram)] + gpus

        msg = Float32MultiArray()
        # Optionally, you could fill layout.dim here — for simple consumers data is enough
        msg.data = [float(x) for x in payload]

        self.pub.publish(msg)

        # Optional: log occasionally without spamming
        self.get_logger().debug(f'Published: cpu={cpu:.1f}% ram={ram:.1f}% gpus={gpus}')


def main(args=None):
    rclpy.init(args=args)
    node = UtilPublisher(topic_name='resource_monitor', publish_hz=1.0)  # 1 Hz by default
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Shutting down')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
