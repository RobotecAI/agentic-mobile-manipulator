// Type shims for the ROS 2 messages this HMI consumes/produces.
// Field names match the ROS message definitions exactly (roslibjs passes JSON).

export interface Header {
  stamp?: { sec: number; nanosec: number };
  frame_id?: string;
}

/** demo_msgs/Utilization */
export interface Utilization {
  component_names: string[];
  component_values: number[];
  nav2_state: boolean;
  moveit2_state: boolean;
}

/** sensor_msgs/Image (raw) — only the fields we touch */
export interface RosImage {
  height: number;
  width: number;
  encoding: string;
  data: string | number[]; // base64 over rosbridge
}

/** demo_msgs/VlmDescription */
export interface VlmDescription {
  image: RosImage;
  description: string;
  source: string;
}

/** rcl_interfaces/Log */
export interface RosLog {
  level: number; // 10 DEBUG, 20 INFO, 30 WARN, 40 ERROR, 50 FATAL
  name: string;
  msg: string;
  function?: string;
}

/** rai_interfaces/HRIMessage (subset) */
export interface HRIMessage {
  text: string;
  communication_id: string;
}

/** nav_msgs/OccupancyGrid */
export interface OccupancyGrid {
  info: {
    resolution: number;
    width: number;
    height: number;
    origin: {
      position: { x: number; y: number; z: number };
      orientation: { x: number; y: number; z: number; w: number };
    };
  };
  data: number[];
}

/** geometry_msgs/PoseStamped */
export interface PoseStamped {
  header: Header;
  pose: {
    position: { x: number; y: number; z: number };
    orientation: { x: number; y: number; z: number; w: number };
  };
}

/** nav_msgs/Path */
export interface Path {
  header: Header;
  poses: PoseStamped[];
}

/** std_msgs/String */
export interface StringMsg {
  data: string;
}

export type ConnectionState = "connecting" | "connected" | "closed" | "demo";

export interface ServiceResult {
  success: boolean;
  message: string;
}
