import subprocess
import psutil
import time
import threading
import signal
import sys
import os
import csv
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from collections import defaultdict
import statistics
from ollama import Client
import argparse
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
from rclpy.node import Node
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from geometry_msgs.msg import Point, Pose, Quaternion

from rai_interfaces.srv import ManipulatorMoveTo


class MoveItClient(Node):
    def __init__(self):
        super().__init__("moveit_action_client")
        self.action_name = "/move_action"
        self.action_client = ActionClient(self, MoveGroup, "/move_action")
        self.manipulator_frame = "panda_link0"
        self.quaternion = Quaternion(
            x=0.9238795325112867, y=-0.3826834323650898, z=0.0, w=0.0
        )
        self.additional_height = 0.05
        self.min_z = 0.135

    def wait_for_server(self, timeout=10.0):
        """Wait for MoveIt action server"""
        self.get_logger().info("Waiting for MoveIt action server...")
        if not self.action_client.wait_for_server(timeout_sec=timeout):
            self.get_logger().error(
                f"MoveIt action server: {self.action_name} not available!"
            )
            return False
        return True

    def move_to_pose(
        self,
        x: float,
        y: float,
        z: float,
        task: Literal["grab", "drop"],
    ):
        """Move end effector to specified pose"""
        client = self.create_client(ManipulatorMoveTo, "/manipulator_move_to")

        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = self.manipulator_frame
        pose_stamped.pose = Pose(
            position=Point(x=x, y=y, z=z),
            orientation=self.quaternion,
        )

        if task == "drop":
            pose_stamped.pose.position.z += self.additional_height

        pose_stamped.pose.position.z = np.max(
            [pose_stamped.pose.position.z, self.min_z]
        )

        request = ManipulatorMoveTo.Request()
        request.target_pose = pose_stamped

        if task == "grab":
            request.initial_gripper_state = True  # open
            request.final_gripper_state = False  # closed
        else:
            request.initial_gripper_state = False  # closed
            request.final_gripper_state = True  # open

        client.call_async(request)
        self.get_logger().debug(
            f"Calling ManipulatorMoveTo service with request: x={request.target_pose.pose.position.x:.2f}, y={request.target_pose.pose.position.y:.2f}, z={request.target_pose.pose.position.z:.2f}"
        )


class ProcessManager:
    def __init__(self, model_vl: str, model_llm: str, use_gpu: bool) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = f"monitoring_results_{self.timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)

        self.processes: Dict[str, Dict[str, Any]] = {}
        self.monitoring: bool = True
        self.monitor_thread: Optional[threading.Thread] = None
        self.error_monitor_thread: Optional[threading.Thread] = None

        self.log_file: str = os.path.join(
            self.output_dir,
            f"resource_monitor_{self.timestamp}_{model_vl}_{model_llm}_gpu-{use_gpu}.log",
        )
        self.error_log_file: str = os.path.join(
            self.output_dir,
            f"error_log_{self.timestamp}_{model_vl}_{model_llm}_gpu-{use_gpu}.log",
        )
        self.csv_file: str = os.path.join(
            self.output_dir,
            f"resource_metrics_{self.timestamp}_{model_vl}_{model_llm}_gpu-{use_gpu}.csv",
        )
        self.infer_csv_file: str = os.path.join(
            self.output_dir,
            f"tokens_metrics_{self.timestamp}_{model_vl}_{model_llm}_gpu-{use_gpu}.csv",
        )
        self.stats_file: str = os.path.join(
            self.output_dir,
            f"resource_stats_{self.timestamp}_{model_vl}_{model_llm}_gpu-{use_gpu}.json",
        )

        self.init_csv_files()

        self.resource_stats: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.system_stats: Dict[str, List[float]] = defaultdict(list)
        self.infer_metrics: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def init_csv_files(self) -> None:
        with open(self.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "process_name",
                    "cpu_percent",
                    "memory_mb",
                    "process_count",
                    "system_cpu_percent",
                    "system_memory_percent",
                    "system_memory_available_gb",
                ]
            )

        with open(self.infer_csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "model_name",
                    "input_tokens_per_sec",
                    "output_tokens_per_sec",
                    "eval_count",
                    "eval_duration",
                    "prompt_eval_count",
                    "prompt_eval_duration",
                ]
            )

    def launch_ollama_server(self, port: int = 11434, gpu: bool = False) -> bool:
        print("Launching Ollama server")

        env: Dict[str, str] = os.environ.copy()
        if gpu:
            env.update({"CUDA_VISIBLE_DEVICES": "0"})
        else:
            env.update({"CUDA_VISIBLE_DEVICES": "", "OLLAMA_NUM_GPU": "0"})

        env.update(
            {
                "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/lib/ollama",
                "PATH": env.get("PATH", "") + ":/usr/local/cuda/bin",
                "OLLAMA_HOST": f"0.0.0.0:{port}",
            }
        )

        ollama_serve: subprocess.Popen = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        time.sleep(3)

        if ollama_serve.poll() is not None:
            stdout, stderr = ollama_serve.communicate()
            print("Ollama serve failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

        self.processes[f"ollama_serve_{port}"] = {
            "process": ollama_serve,
            "type": "ollama_serve",
            "port": port,
            "stdout": ollama_serve.stdout,
            "stderr": ollama_serve.stderr,
        }

        print("Ollama server launched successfully")
        return True

    def launch_ros2_moveit(self) -> bool:
        print("Launching ROS2 MoveIt")

        moveit_process: subprocess.Popen = subprocess.Popen(
            ["./run-moveit.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(5)
        if moveit_process.poll() is not None:
            stdout, stderr = moveit_process.communicate()
            print("ROS2 MoveIt failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

        self.processes["ros2_moveit"] = {
            "process": moveit_process,
            "type": "ros2_moveit",
            "stdout": moveit_process.stdout,
            "stderr": moveit_process.stderr,
        }

        print("ROS2 MoveIt launched")
        return True

    def launch_ros2_nav2(self, map_file: Optional[str] = "map.yaml") -> bool:
        print("Launching ROS2 Nav2")
        nav2_process: subprocess.Popen = subprocess.Popen(
            ["./run-nav.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(3)
        if nav2_process.poll() is not None:
            stdout, stderr = nav2_process.communicate()
            print("ROS2 Nav2 failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

        self.processes["ros2_nav2"] = {
            "process": nav2_process,
            "type": "ros2_nav2",
            "map_file": map_file,
            "stdout": nav2_process.stdout,
            "stderr": nav2_process.stderr,
        }

        print("ROS2 Nav2 launched")
        return True

    def get_process_tree_resources(
        self, process: subprocess.Popen
    ) -> Optional[Dict[str, Any]]:
        parent: psutil.Process = psutil.Process(process.pid)
        processes: List[psutil.Process] = [parent] + parent.children(recursive=True)

        total_cpu: float = 0
        total_memory: int = 0

        self.check_process_health()
        for proc in processes:
            try:
                total_cpu += proc.cpu_percent(0.1)
                total_memory += proc.memory_info().rss
            except psutil.NoSuchProcess:
                print(f"No such process: {proc}")
        return {
            "cpu_percent": total_cpu,
            "memory_mb": total_memory / 1024 / 1024,
            "process_count": len(processes),
        }

    def log_metrics_to_csv(
        self,
        timestamp: str,
        process_name: str,
        resources: Dict[str, Any],
        system_stats: Dict[str, float],
    ) -> None:
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    timestamp,
                    process_name,
                    resources["cpu_percent"],
                    round(resources["memory_mb"], 2),
                    resources["process_count"],
                    system_stats["system_cpu_percent"],
                    system_stats["system_memory_percent"],
                    round(system_stats["memory_available_gb"], 2),
                ]
            )

    def log_tokens_to_csv(
        self,
        timestamp: str,
        model_name: str,
        input_tokens_per_sec: float,
        output_tokens_per_sec: float,
        eval_count: int,
        eval_duration: int,
        prompt_eval_count: int,
        prompt_eval_duration: int,
    ) -> None:
        with open(self.infer_csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    timestamp,
                    model_name,
                    round(input_tokens_per_sec, 3),
                    round(output_tokens_per_sec, 3),
                    eval_count,
                    eval_duration,
                    prompt_eval_count,
                    prompt_eval_duration,
                ]
            )

    def update_statistics(
        self,
        process_name: str,
        resources: Dict[str, Any],
        system_stats: Dict[str, float],
    ) -> None:
        self.resource_stats[process_name]["cpu_percent"].append(
            resources["cpu_percent"]
        )
        self.resource_stats[process_name]["memory_mb"].append(resources["memory_mb"])

        self.system_stats["cpu_percent"].append(system_stats["system_cpu_percent"])
        self.system_stats["memory_percent"].append(
            system_stats["system_memory_percent"]
        )
        self.system_stats["memory_available_gb"].append(
            system_stats["memory_available_gb"]
        )

    def update_token_statistics(
        self, model: str, input_tokens_per_sec: float, output_tokens_per_sec: float
    ) -> None:
        self.infer_metrics[model]["input_tokens_per_sec"].append(input_tokens_per_sec)
        self.infer_metrics[model]["output_tokens_per_sec"].append(output_tokens_per_sec)

    def update_total_statistics(
        self, total_cpu: float, total_memory: float, total_processes: int
    ) -> None:
        # Track totals for all processes combined
        if not hasattr(self, "total_stats"):
            self.total_stats = {"cpu_percent": [], "memory_mb": [], "process_count": []}

        self.total_stats["cpu_percent"].append(total_cpu)
        self.total_stats["memory_mb"].append(total_memory)
        self.total_stats["process_count"].append(total_processes)

    def calculate_statistics(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "process_stats": {},
            "system_stats": {},
            "token_stats": defaultdict(dict),
            "total_stats": {},
        }

        for process_name, metrics in self.resource_stats.items():
            stats["process_stats"][process_name] = {}
            for metric_name, values in metrics.items():
                if values:
                    stats["process_stats"][process_name][metric_name] = {
                        "max": round(max(values), 3),
                        "average": round(statistics.mean(values), 3),
                    }

        for metric_name, values in self.system_stats.items():
            if values:
                stats["system_stats"][metric_name] = {
                    "max": round(max(values), 3),
                    "average": round(statistics.mean(values), 3),
                }

        # NOTE (jmatejcz) we don't take the first measurement
        # as the processing input in the first call after loading takes
        # 10x time
        for model_name, data in self.infer_metrics.items():
            for metric_name, values in data.items():
                if values:
                    values = values[1:]
                    stats["token_stats"][model_name][metric_name] = {
                        "max": round(max(values), 3),
                        "min": round(min(values), 3),
                        "average": round(statistics.mean(values), 3),
                    }

        # Calculate statistics for total process usage
        if hasattr(self, "total_stats"):
            for metric_name, values in self.total_stats.items():
                if values:
                    stats["total_stats"][metric_name] = {
                        "max": round(max(values), 3),
                        "average": round(statistics.mean(values), 3),
                    }

        return stats

    def print_statistics(self) -> None:
        stats: Dict[str, Any] = self.calculate_statistics()

        print("\n" + "=" * 60)

        for process_name, metrics in stats["process_stats"].items():
            print(f"\nProcess: {process_name}")
            print("-" * 60)
            for metric_name, values in metrics.items():
                print(
                    f"{metric_name:15} | Max: {values['max']:8.2f} | Avg: {values['average']:8.2f}"
                )

        # Print total statistics for all processes combined
        if stats["total_stats"]:
            print("\nTotal Process Statistics (All Processes Combined)")
            print("-" * 60)
            for metric_name, values in stats["total_stats"].items():
                unit = (
                    "%"
                    if "percent" in metric_name
                    else ("MB" if "memory" in metric_name else "")
                )
                print(
                    f"{metric_name:15} | Max: {values['max']:8.2f}{unit} | Avg: {values['average']:8.2f}{unit}"
                )

        if stats["system_stats"]:
            print("\nSystem Statistics")
            print("-" * 60)
            for metric_name, values in stats["system_stats"].items():
                unit = "%" if "percent" in metric_name else "GB"
                print(
                    f"{metric_name:20} | Max: {values['max']:8.2f}{unit} |  Avg: {values['average']:8.2f}{unit}"
                )

        if stats["token_stats"]:
            print("\nToken Processing Statistics")
            print("-" * 60)
            for model_name, data in stats["token_stats"].items():
                for metric_name, values in data.items():
                    print(
                        f"{model_name}: {metric_name:20} | Max: {values['max']:8.2f} | Min: {values['min']:8.2f} | Avg: {values['average']:8.2f}"
                    )

    def save_statistics(self) -> None:
        stats: Dict[str, Any] = self.calculate_statistics()

        stats["metadata"] = {
            "processes_monitored": list(self.resource_stats.keys()),
        }

        with open(self.stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        print(f"Statistics saved to: {self.stats_file}")

    def monitor_resources(self) -> None:
        while self.monitoring:
            timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_stats: Dict[str, float] = defaultdict(float)

            print(f"\nResource Monitor - {timestamp}")
            print("-" * 60)

            system_cpu: float = psutil.cpu_percent()
            system_memory: psutil._psutil_common.svmem = psutil.virtual_memory()
            system_stats: Dict[str, float] = {
                "system_cpu_percent": system_cpu,
                "system_memory_percent": system_memory.percent,
                "memory_available_gb": system_memory.available / 1024 / 1024 / 1024,
            }

            self.system_stats["cpu_percent"].append(system_cpu)
            self.system_stats["memory_percent"].append(system_memory.percent)
            self.system_stats["memory_available_gb"].append(
                system_memory.available / 1024 / 1024 / 1024
            )

            for name, proc_info in self.processes.items():
                if proc_info["process"].poll() is None:
                    resources: Optional[Dict[str, Any]] = (
                        self.get_process_tree_resources(proc_info["process"])
                    )

                    if resources:
                        print(
                            f"{name:20} | CPU: {resources['cpu_percent']:6.1f}% | "
                            f"Memory: {resources['memory_mb']:8.1f} MB | "
                            f"Processes: {resources['process_count']:3d}"
                        )

                        self.log_metrics_to_csv(
                            timestamp, name, resources, system_stats
                        )
                        self.update_statistics(name, resources, system_stats)

                        total_stats["cpu"] += resources["cpu_percent"]
                        total_stats["memory"] += resources["memory_mb"]
                        total_stats["processes"] += resources["process_count"]
                else:
                    print(f"{name:20} | Process terminated")

            # Update total statistics with the summed values
            self.update_total_statistics(
                total_stats["cpu"], total_stats["memory"], int(total_stats["processes"])
            )

            self.check_process_health()

            print("-" * 60)
            print(
                f"{'TOTAL':20} | CPU: {total_stats['cpu']:6.1f}% | "
                f"Memory: {total_stats['memory']:8.1f} MB | "
                f"Processes: {total_stats['processes']:3.0f}"
            )

            print(
                f"{'SYSTEM':20} | CPU: {system_cpu:6.1f}% | "
                f"Memory: {system_memory.percent:6.1f}% | "
                f"Available: {system_memory.available/1024/1024/1024:.1f} GB"
            )

            time.sleep(0.1)

    def check_process_health(self) -> None:
        for name, proc_info in list(self.processes.items()):
            process: subprocess.Popen = proc_info["process"]
            if process.poll() is not None:
                timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return_code: Optional[int] = process.returncode

                if return_code != 0:
                    print(f"PROCESS DIED [{name}] {timestamp}: Exit code {return_code}")

                    stdout, stderr = process.communicate(timeout=1)
                    if stdout:
                        print(f"Final STDOUT [{name}]: {stdout.decode()}")
                    if stderr:
                        print(f"Final STDERR [{name}]: {stderr.decode()}")

                    with open(self.error_log_file, "a") as f:
                        f.write(
                            f"[{timestamp}] {name} DIED - Exit code: {return_code}\n"
                        )
                        if stderr:
                            f.write(f"STDERR: {stderr.decode()}\n")
                        f.write("-" * 50 + "\n")

    def start_monitoring(self) -> None:
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        print(f"Resource monitoring started - logging to {self.log_file}")
        print(f"CSV metrics logging to {self.csv_file}")
        print(f"Token metrics logging to {self.infer_csv_file}")

    def stop_all_processes(self) -> None:
        print("\nStopping all processes...")
        self.monitoring = False

        for name, proc_info in self.processes.items():
            process: subprocess.Popen = proc_info["process"]
            if process.poll() is None:
                print(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"{name} stopped")

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        if self.error_monitor_thread:
            self.error_monitor_thread.join(timeout=1)

        print("All processes stopped")

    def get_process_logs(self, process_name: str) -> None:
        if process_name not in self.processes:
            print(f"Process {process_name} not found")
            return

        proc_info: Dict[str, Any] = self.processes[process_name]

        print(f"Logs for {process_name}:")
        print("=" * 50)

        stdout: Optional[Any] = proc_info.get("stdout")
        stderr: Optional[Any] = proc_info.get("stderr")

        if stdout:
            print("STDOUT:")
            import select

            if select.select([stdout], [], [], 0.1)[0]:
                content: str = stdout.read().decode()
                print(content if content else "No stdout content")
            else:
                print("No new stdout content")
            print("-" * 30)

        if stderr:
            print("STDERR:")
            import select

            if select.select([stderr], [], [], 0.1)[0]:
                content: str = stderr.read().decode()
                print(content if content else "No stderr content")
            else:
                print("No new stderr content")

    def list_processes(self) -> None:
        print("\nProcess Status:")
        print("=" * 60)

        for name, proc_info in self.processes.items():
            process: subprocess.Popen = proc_info["process"]
            status: str = (
                "Running"
                if process.poll() is None
                else f"Stopped (code: {process.returncode})"
            )
            proc_type: str = proc_info["type"]

            print(f"{name:25} | {status:20} | Type: {proc_type}")

    def make_call_to_model(self, model: str):
        client = Client(host="0.0.0.0:11434", timeout=120)
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            response = client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Explain the concept of artificial intelligence in simple terms in around 200 words",
                    },
                ],
                keep_alive=500,
            )
            output_tokens_per_sec: float = (
                response["eval_count"] / response["eval_duration"] * 1_000_000_000
            )
            input_tokens_per_sec: float = (
                response["prompt_eval_count"]
                / response["prompt_eval_duration"]
                * 1_000_000_000
            )

            print(f"{model}, Input tokens/sec: {input_tokens_per_sec:.2f}")
            print(f"{model}, Output tokens/sec: {output_tokens_per_sec:.2f}")

            self.log_tokens_to_csv(
                timestamp,
                model,
                input_tokens_per_sec,
                output_tokens_per_sec,
                response["eval_count"],
                response["eval_duration"],
                response["prompt_eval_count"],
                response["prompt_eval_duration"],
            )

            self.update_token_statistics(
                model, input_tokens_per_sec, output_tokens_per_sec
            )
        except Exception as e:
            print(f"Failed to query {model}: {e}")

    def launch_agent_process(self, model: str = "qwen2.5:7b") -> bool:
        print(f"Launching Agent Process with model {model}")

        agent_process = subprocess.Popen(
            [sys.executable, "agent_process.py", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(2)  # Give it time to start

        if agent_process.poll() is not None:
            stdout, stderr = agent_process.communicate()
            print("Agent process failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

        self.processes["agent_process"] = {
            "process": agent_process,
            "type": "agent",
            "model": model,
            "stdout": agent_process.stdout,
            "stderr": agent_process.stderr,
        }

        print("Agent process launched successfully")
        return True


def signal_handler(signum: int, frame: Any) -> None:
    print(f"\nReceived signal {signum}")
    manager.stop_all_processes()
    manager.print_statistics()
    manager.save_statistics()
    sys.exit(0)


def main(model_vl: str, model_llm: str, sim: Literal['navigation','manipulation'], use_gpu=False, run_time: int = 180) -> None:

    global manager
    manager = ProcessManager(model_vl=model_vl, model_llm=model_llm, use_gpu=use_gpu)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Multi-Process Launcher Starting...")
    print("=" * 60)
    if not manager.launch_ollama_server(port=11434, gpu=use_gpu):
        print("Failed to launch Ollama server")
        return

    if not manager.launch_ros2_nav2(map_file="medium_random.pgm"):
        print("Failed to launch nav2")
        return

    if not manager.launch_ros2_moveit():
        print("Failed to launch moveit")
        return

    if not manager.launch_agent_process(model_llm):
        print("Failed to launch agent process")
        return

    time.sleep(2)

    manager.start_monitoring()

    print("\nAll processes launched successfully!")
    print(f"Running for {run_time} seconds with monitoring...")
    print("=" * 60)

    start_time: float = time.time()
    end_time: float = start_time + run_time

    rclpy.init()
    navigator = BasicNavigator()

    # goal pose
    goal_1_pose = PoseStamped()
    goal_1_pose.header.frame_id = "map"
    goal_1_pose.header.stamp = navigator.get_clock().now().to_msg()
    goal_1_pose.pose.position.x = 1.0
    goal_1_pose.pose.position.y = 1.0
    goal_1_pose.pose.position.z = 0.0
    goal_1_pose.pose.orientation.w = 1.0

    goal_2_pose = PoseStamped()
    goal_2_pose.header.frame_id = "map"
    goal_2_pose.header.stamp = navigator.get_clock().now().to_msg()
    goal_2_pose.pose.position.x = -1.0
    goal_2_pose.pose.position.y = -1.0
    goal_2_pose.pose.position.z = 0.0
    goal_2_pose.pose.orientation.w = 1.0

    move_client = MoveItClient()
    even = True

    while time.time() < end_time:
        # switch the points
        manager.make_call_to_model(model=model_vl)
        manager.make_call_to_model(model=model_llm)
        if even:
            if sim == 'navigation':
                if navigator.isTaskComplete():
                    navigator.goToPose(goal_1_pose)
            elif sim == 'manipulation':
                move_client.move_to_pose(0.3, 0.0, 0.5, "grab")
            even = False
        else:
            if sim == 'navigation':
                if navigator.isTaskComplete():
                    navigator.goToPose(goal_2_pose)
            elif sim == 'manipulation':
                move_client.move_to_pose(0.0, 0.3, 0.1, "drop")
            even = True

    print(f"\n{run_time} seconds completed!")
    print(f"Resource metrics saved to: {manager.csv_file}")
    print(f"Token metrics saved to: {manager.infer_csv_file}")
    print(f"All files saved to directory: {manager.output_dir}")

    manager.print_statistics()

    manager.stop_all_processes()
    move_client.destroy_node()
    navigator.destroyNode()
    rclpy.shutdown()

    manager.print_statistics()
    manager.save_statistics()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Multi-Process Launcher for ROS2 and Ollama"
    )

    parser.add_argument(
        "--run-time", type=int, default=180, help="Runtime in seconds (default: 180)"
    )

    parser.add_argument(
        "--model-vl",
        type=str,
        default="qwen2.5vl:3b",
        help="Vision-language model name (default: qwen2.5vl:3b)",
    )

    parser.add_argument(
        "--model-llm",
        type=str,
        default="qwen2.5:7b",
        help="LLM model name (default: qwen2.5:7b)",
    )
    parser.add_argument("--sim", type=str, required=True, choices=["navigation", "manipulation"], help="Simulation type")
    parser.add_argument("--use-gpu", action=argparse.BooleanOptionalAction)
    parser.set_defaults(use_gpu=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(
        run_time=args.run_time,
        model_vl=args.model_vl,
        model_llm=args.model_llm,
        use_gpu=args.use_gpu,
        sim=args.sim,
    )
