#!/usr/bin/env python3
# Copyright (C) 2025 Robotec.ai sp. z o.o. — Apache-2.0
#
# Mock ROS 2 data source for the Kairos+ Web HMI.
#
# Publishes every topic the HMI subscribes to, serves the scenario/restart
# services, and reacts to the commands the HMI publishes (free-form tasks,
# e-stop, teleop, goals) so the UI feels alive end-to-end over rosbridge.
#
# Usage:
#   source /opt/ros/jazzy/setup.bash
#   source <repo>/ros2_ws/install/setup.bash      # for demo_msgs
#   python3 web_hmi/tools/mock_ros_publisher.py
#
# Then run rosbridge (ros2 launch rosbridge_server rosbridge_websocket_launch.xml)
# and open the HMI. Topics/types mirror web_hmi/src/ros/config.ts.

import math
import random

try:
    import numpy as np
except ImportError:  # numpy ships with the ROS 2 python env, but degrade gracefully
    np = None

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy, QoSHistoryPolicy

from std_msgs.msg import String, Header
from std_srvs.srv import Trigger
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from sensor_msgs.msg import Image

from demo_msgs.msg import Utilization, VlmDescription
from rai_interfaces.msg import HRIMessage


VLM_LINES = [
    ("Inspection", "Aisle B clear. Pallet jack parked correctly against the wall."),
    ("Safety", "Possible liquid spill detected near rack C02 — flagging for review."),
    ("Inspection", "Returned package on conveyor identified: cardboard box, ~40cm."),
    ("Safety", "Path to packing table unobstructed. No personnel in the work cell."),
    ("Inspection", "Rack B02 slot 3 empty — candidate destination for sorted item."),
]

ACTIONS = [
    "Calling Tool navigate_to with params target: returns_area",
    "Calling Tool detect_objects with params camera: wrist",
    "Calling Tool pick_object with params id: package_14",
    "Calling Tool navigate_to with params target: rack_B02",
    "Calling Tool place_object with params slot: B02-3",
]

ROSOUT = [
    ("info", "nav2_bt_navigator", "Begin navigating to (3.20, 4.80)"),
    ("info", "nav2_planner", "Plan computed: 24 poses, 11.4 m"),
    ("warn", "nav2_controller", "Speed limit reduced near detected obstacle"),
    ("info", "moveit2", "Pick motion executed successfully"),
]


def build_map():
    w, h = 160, 160
    grid = OccupancyGrid()
    grid.header.frame_id = "map"
    grid.info.resolution = 0.2
    grid.info.width = w
    grid.info.height = h
    grid.info.origin.position.x = -16.0
    grid.info.origin.position.y = -16.0
    grid.info.origin.orientation.w = 1.0
    data = [0] * (w * h)

    def occ(x, y):
        if 0 <= x < w and 0 <= y < h:
            data[y * w + x] = 100

    for x in range(w):
        occ(x, 4)
        occ(x, h - 5)
    for y in range(h):
        occ(4, y)
        occ(w - 5, y)
    for r in range(4):
        x0 = 30 + r * 28
        for y in range(30, 120):
            occ(x0, y)
            occ(x0 + 1, y)
    for x in range(30, 70):
        occ(x, 130)
    grid.data = data
    return grid


def build_image():
    img = Image()
    img.height, img.width = 90, 120
    img.encoding = "rgba8"
    img.step = img.width * 4
    buf = bytearray(img.width * img.height * 4)
    for y in range(img.height):
        for x in range(img.width):
            i = (y * img.width + x) * 4
            buf[i] = int(255 * x / img.width)
            buf[i + 1] = int(120 + 80 * math.sin(y / 12.0))
            buf[i + 2] = int(255 * y / img.height)
            buf[i + 3] = 255
    img.data = bytes(buf)
    return img


class MockPublisher(Node):
    def __init__(self):
        super().__init__("hmi_mock_publisher")

        latched = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
        )

        # --- publishers ---
        self.pub_util = self.create_publisher(Utilization, "/utilization", 10)
        self.pub_heart = self.create_publisher(Header, "/orchestrator/heartbeat", 10)
        self.pub_task = self.create_publisher(String, "/orchestrator/current_task", latched)
        self.pub_past = self.create_publisher(String, "/agent/past_steps", latched)
        self.pub_queue = self.create_publisher(String, "/orchestrator/tasks_queue", latched)
        self.pub_paused = self.create_publisher(String, "/orchestrator/paused_tasks", latched)
        self.pub_action = self.create_publisher(HRIMessage, "/agent/current_action", 10)
        self.pub_vlm = self.create_publisher(VlmDescription, "/vlm_topic", 10)
        self.pub_map = self.create_publisher(OccupancyGrid, "/global_costmap/static_layer", latched)
        self.pub_plan = self.create_publisher(Path, "/plan", 10)

        # --- camera streams (picked up by web_video_server -> MJPEG) ---
        # topic -> (RGB tint weights). Matches CAMERAS in web_hmi/src/ros/config.ts.
        self.cams = {
            "/rgbd_camera/camera_image_color": (0.7, 0.85, 1.15),  # base — cool/blue
            "/wrist_camera/camera_image_color": (1.2, 0.8, 0.75),  # wrist — warm/red
            "/camera_image_color": (0.8, 1.15, 0.85),              # top — green
        }
        self.cam_w, self.cam_h = 320, 240
        self.cam_pubs = {t: self.create_publisher(Image, t, 5) for t in self.cams}

        # --- services (scenario / restart) ---
        for name in [
            "/restart",
            "/rai/scene/standard",
            "/rai/scene/housekeep",
            "/rai/scene/anomalies",
            "/rai/scene/cleanup",
        ]:
            self.create_service(Trigger, name, self._make_trigger(name))

        # --- subscriptions (react to HMI output) ---
        self.create_subscription(String, "/user_tasks", self.on_user_task, 10)
        self.create_subscription(String, "/emergency_stop", self.on_estop, 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.create_subscription(PoseStamped, "/goal_pose", self.on_goal, 10)

        # --- state ---
        self.map = build_map()
        self.image = build_image()
        self.halted = False
        self.t = 0.0
        self.action_i = 0
        self.vlm_i = 0
        self.rosout_i = 0
        self.current_task = "Sort package returns from the returns area"
        self.past = ["Reached returns area", "Identified 3 packages", "Picked package 14"]
        self.queue = ["Place package 14 on rack B02", "Return for package 15", "Update inventory log"]

        # --- timers ---
        self.create_timer(0.2, self.tick_fast)      # plan / time base
        self.create_timer(1.0, self.tick_1hz)       # heartbeat + utilization
        self.create_timer(2.0, self.tick_map)       # republish latched map
        self.create_timer(2.5, self.tick_lists)     # task/queue/history
        self.create_timer(3.0, self.tick_action)    # current action
        self.create_timer(3.5, self.tick_rosout)    # log events
        self.create_timer(5.0, self.tick_vlm)       # vlm descriptions
        self.create_timer(0.1, self.tick_cameras)   # ~10 Hz camera noise

        self.tick_map()
        self.tick_lists()
        self.get_logger().info("Mock HMI publisher running. Connect rosbridge + open the HMI.")

    # ---- services ----
    def _make_trigger(self, name):
        def handler(_req, resp):
            self.get_logger().info(f"service {name} called")
            self.halted = False
            if name != "/restart":
                self.current_task = f"Scenario staged: {name.split('/')[-1]}"
            resp.success = True
            resp.message = f"{name} ok"
            return resp
        return handler

    # ---- reactions to HMI commands ----
    def on_user_task(self, msg: String):
        self.get_logger().info(f"/user_tasks received: {msg.data}")
        self.halted = False
        self.current_task = msg.data
        self.past = []
        self.queue = ["Plan steps for: " + msg.data[:40], "Execute", "Report result"]
        self.tick_lists()

    def on_estop(self, _msg: String):
        self.get_logger().warn("EMERGENCY STOP received — halting agent")
        self.halted = True
        self.current_task = "HALTED — emergency stop engaged"
        self.tick_lists()

    def on_cmd_vel(self, msg: Twist):
        if abs(msg.linear.x) > 1e-3 or abs(msg.angular.z) > 1e-3:
            self.get_logger().info(f"/cmd_vel lin={msg.linear.x:.2f} ang={msg.angular.z:.2f}")

    def on_goal(self, msg: PoseStamped):
        p = msg.pose.position
        self.get_logger().info(f"/goal_pose ({p.x:.2f}, {p.y:.2f})")

    # ---- periodic publishing ----
    def tick_fast(self):
        self.t += 0.2
        path = Path()
        path.header.frame_id = "map"
        for i in range(25):
            s = i / 24.0
            ps = PoseStamped()
            ps.header.frame_id = "map"
            ps.pose.position.x = -8 + s * 12 + math.sin(self.t / 6 + s * 6) * 1.5
            ps.pose.position.y = -6 + s * 9
            ps.pose.orientation.w = 1.0
            path.poses.append(ps)
        self.pub_plan.publish(path)

    def tick_1hz(self):
        if not self.halted:
            self.pub_heart.publish(Header(frame_id="orchestrator"))

        def wig(base, amp, ph):
            return max(0.0, min(100.0, base + math.sin(self.t / 4 + ph) * amp + random.uniform(-3, 3)))

        u = Utilization()
        u.component_names = ["cpu", "ram", "gpu", "disk", "vram"]
        u.component_values = [wig(46, 18, 0), wig(63, 8, 1), wig(72, 20, 2), 94.0, wig(58, 14, 3)]
        u.nav2_state = not self.halted
        u.moveit2_state = not self.halted
        self.pub_util.publish(u)

    def tick_map(self):
        self.map.header.stamp = self.get_clock().now().to_msg()
        self.pub_map.publish(self.map)

    def tick_lists(self):
        self.pub_task.publish(String(data=self.current_task))
        self.pub_past.publish(String(data="[" + " | ".join(f'"{s}"' for s in self.past) + "]"))
        self.pub_queue.publish(String(data="[" + " | ".join(f'"{s}"' for s in self.queue) + "]"))
        self.pub_paused.publish(String(data="[]"))

    def tick_action(self):
        if self.halted:
            return
        a = ACTIONS[self.action_i % len(ACTIONS)]
        self.action_i += 1
        self.pub_action.publish(HRIMessage(text=a, communication_id=str(self.action_i)))
        # occasionally advance the plan to make history grow
        if self.action_i % 3 == 0 and self.queue:
            self.past.append(self.queue.pop(0))
            if not self.queue:
                self.queue = ["Return to dock", "Await next dispatch"]
            self.tick_lists()

    def tick_rosout(self):
        level, name, msg = ROSOUT[self.rosout_i % len(ROSOUT)]
        self.rosout_i += 1
        logger = self.get_logger().get_child(name)
        (logger.warn if level == "warn" else logger.info)(msg)

    def _noise_frame(self, tint):
        w, h, t = self.cam_w, self.cam_h, self.t
        if np is not None:
            # random static + a drifting brightness wave so it reads as "live"
            frame = np.random.randint(0, 200, (h, w, 3), dtype=np.uint8).astype(np.float32)
            wave = (np.sin(np.linspace(0, 6.28, w) + t * 3.0) * 35 + 35).astype(np.float32)
            frame += wave[None, :, None]
            frame *= np.array(tint, dtype=np.float32)[None, None, :]
            np.clip(frame, 0, 255, out=frame)
            return frame.astype(np.uint8).tobytes()
        # numpy-free fallback: pure random noise
        return bytes(random.getrandbits(8) for _ in range(w * h * 3))

    def tick_cameras(self):
        stamp = self.get_clock().now().to_msg()
        for topic, tint in self.cams.items():
            img = Image()
            img.header.stamp = stamp
            img.header.frame_id = "camera"
            img.height = self.cam_h
            img.width = self.cam_w
            img.encoding = "rgb8"
            img.step = self.cam_w * 3
            img.data = self._noise_frame(tint)
            self.cam_pubs[topic].publish(img)

    def tick_vlm(self):
        if self.halted:
            return
        source, desc = VLM_LINES[self.vlm_i % len(VLM_LINES)]
        self.vlm_i += 1
        m = VlmDescription()
        m.image = self.image
        m.description = desc
        m.source = source
        self.pub_vlm.publish(m)


def main():
    rclpy.init()
    node = MockPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
