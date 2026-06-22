// Central registry of every ROS interface the HMI touches, plus connection
// settings. Mirrors the topic/service names used by the native Qt HMI.

function param(key: string, fallback: string): string {
  const q = new URLSearchParams(window.location.search).get(key);
  if (q) return q;
  const ls = window.localStorage.getItem(`hmi.${key}`);
  if (ls) return ls;
  const env = (import.meta.env as Record<string, string | undefined>)[`VITE_${key.toUpperCase()}`];
  return env ?? fallback;
}

const host = window.location.hostname || "localhost";

export const CONFIG = {
  /** rosbridge_server websocket (ros2 run rosbridge_server rosbridge_websocket). */
  rosbridgeUrl: param("rosbridge", `ws://${host}:9090`),
  /** web_video_server base (ros2 run web_video_server web_video_server). */
  videoServerUrl: param("video", `http://${host}:8080`),
  /** force the synthetic demo feed even if rosbridge is reachable. */
  forceDemo: param("demo", "0") === "1",
};

/** Topics the HMI subscribes to. */
export const TOPICS = {
  utilization: { name: "/utilization", type: "demo_msgs/msg/Utilization" },
  vlm: { name: "/vlm_topic", type: "demo_msgs/msg/VlmDescription" },
  rosout: { name: "/rosout", type: "rcl_interfaces/msg/Log" },
  currentAction: { name: "/agent/current_action", type: "rai_interfaces/msg/HRIMessage" },
  currentTask: { name: "/orchestrator/current_task", type: "std_msgs/msg/String" },
  pastSteps: { name: "/agent/past_steps", type: "std_msgs/msg/String" },
  taskQueue: { name: "/orchestrator/tasks_queue", type: "std_msgs/msg/String" },
  pausedTasks: { name: "/orchestrator/paused_tasks", type: "std_msgs/msg/String" },
  heartbeat: { name: "/orchestrator/heartbeat", type: "std_msgs/msg/Header" },
  map: { name: "/global_costmap/static_layer", type: "nav_msgs/msg/OccupancyGrid" },
  plan: { name: "/plan", type: "nav_msgs/msg/Path" },
} as const;

/** Topics the HMI publishes to. */
export const PUBLISHERS = {
  cmdVel: { name: "/cmd_vel", type: "geometry_msgs/msg/Twist" },
  goal: { name: "/goal_pose", type: "geometry_msgs/msg/PoseStamped" },
  stop: { name: "/emergency_stop", type: "std_msgs/msg/String" },
  userTasks: { name: "/user_tasks", type: "std_msgs/msg/String" },
} as const;

/** std_srvs/Trigger services. */
export const SERVICES = {
  restart: "/restart",
  standard: "/rai/scene/standard",
  housekeep: "/rai/scene/housekeep",
  anomalies: "/rai/scene/anomalies",
  cleanup: "/rai/scene/cleanup",
} as const;

export const CAMERAS = {
  base: "/rgbd_camera/camera_image_color",
  wrist: "/wrist_camera/camera_image_color",
  top: "/camera_image_color",
} as const;

export const PROMPTS = {
  sort: "Do Sort Package Returns",
  housekeepRack: "Do Housekeeping of rack ",
  inspect:
    "Drive the warehouse and inspect for hazards such as spills, blocked paths or " +
    "misplaced items. Report any anomalies you find.",
  shipment: "Prepare shipping of the following items: ",
};

export const RACKS = [
  "J01", "J02", "A01", "A02", "A03", "A04", "A05", "A06", "B01", "B02", "B03", "B04",
  "C01", "C02", "C03", "C04", "D01", "D02", "D03", "D04", "F01", "F02", "F03", "F04",
  "G01", "G02", "G03", "G04", "H01", "H02", "I01", "I02", "K01", "K02", "L01", "L02",
];

export const SHIPMENT_ITEMS = ["hammers", "CPU", "GPU", "pipes", "nails", "motherboard"];

/** Static model roster shown on the Status tab (live telemetry not wired yet). */
export const AI_MODELS = [
  { name: "gpt-oss-20b", role: "orchestrator LLM", port: ":8080", vram: "11.5 GB" },
  { name: "lfm2-vl", role: "VLM hazard analysis", port: ":8081", vram: "3.8 GB" },
  { name: "qwen3-embedding", role: "memory retrieval", port: ":8082", vram: "0.7 GB" },
  { name: "qwen3-reranker", role: "memory ranking", port: ":8083", vram: "0.7 GB" },
];

export type TopicKey = keyof typeof TOPICS;
export type ServiceKey = keyof typeof SERVICES;
export type PublisherKey = keyof typeof PUBLISHERS;
