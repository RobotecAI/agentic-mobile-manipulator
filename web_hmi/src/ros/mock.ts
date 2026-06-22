import type { RosStore } from "./store";
import type { OccupancyGrid, Path } from "./types";

// Synthetic data so the HMI is fully alive without a running ROS 2 stack.
// Shapes match the real messages, so the rest of the app is none the wiser.

function buildMap(): OccupancyGrid {
  const w = 160;
  const h = 160;
  const data = new Array<number>(w * h).fill(0);
  const set = (x: number, y: number, v: number) => {
    if (x >= 0 && x < w && y >= 0 && y < h) data[y * w + x] = v;
  };
  // outer walls
  for (let x = 0; x < w; x++) {
    set(x, 4, 100);
    set(x, h - 5, 100);
  }
  for (let y = 0; y < h; y++) {
    set(4, y, 100);
    set(w - 5, y, 100);
  }
  // racks
  for (let r = 0; r < 4; r++) {
    const x0 = 30 + r * 28;
    for (let y = 30; y < 120; y++) {
      set(x0, y, 100);
      set(x0 + 1, y, 100);
    }
  }
  for (let x = 30; x < 70; x++) set(x, 130, 100);
  return {
    info: {
      resolution: 0.2,
      width: w,
      height: h,
      origin: { position: { x: -16, y: -16, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } },
    },
    data,
  };
}

function buildPath(t: number): Path {
  const poses = [];
  for (let i = 0; i <= 24; i++) {
    const s = i / 24;
    poses.push({
      header: {},
      pose: {
        position: {
          x: -8 + s * 12 + Math.sin(t / 1200 + s * 6) * 1.5,
          y: -6 + s * 9,
          z: 0,
        },
        orientation: { x: 0, y: 0, z: 0, w: 1 },
      },
    });
  }
  return { header: {}, poses };
}

const VLM_LINES: Array<{ source: string; description: string }> = [
  { source: "Inspection", description: "Aisle B clear. Pallet jack parked correctly against the wall." },
  { source: "Safety", description: "⚠ Possible liquid spill detected near rack C02 — flagging for review." },
  { source: "Inspection", description: "Returned package on conveyor identified: cardboard box, ~40cm." },
  { source: "Safety", description: "Path to packing table unobstructed. No personnel in the work cell." },
  { source: "Inspection", description: "Rack B02 slot 3 empty — candidate destination for sorted item." },
];

const ACTIONS = [
  "Calling Tool navigate_to with params target: returns_area",
  "Calling Tool detect_objects with params camera: wrist",
  "Calling Tool pick_object with params id: package_14",
  "Calling Tool navigate_to with params target: rack_B02",
  "Calling Tool place_object with params slot: B02-3",
];

const ROSOUT = [
  { level: 20, name: "nav2_bt_navigator", msg: "Begin navigating to (3.20, 4.80)" },
  { level: 20, name: "hmi_window_node", msg: "Published user task: Do Sort Package Returns" },
  { level: 30, name: "nav2_controller", msg: "Speed limit reduced near detected obstacle" },
  { level: 20, name: "nav2_planner", msg: "Plan computed: 24 poses, 11.4 m" },
  { level: 20, name: "moveit2", msg: "Pick motion executed successfully" },
];

export class MockEngine {
  private timers: number[] = [];
  private store: RosStore;
  private rackIdx = 0;
  private actionIdx = 0;
  private vlmIdx = 0;
  private rosoutIdx = 0;
  private started = 0;

  constructor(store: RosStore) {
    this.store = store;
  }

  start() {
    this.started = performance.now();
    const map = buildMap();
    this.store.set("map", map);
    this.store.set("currentTask", { data: "Sort package returns from the returns area" });
    this.store.set("pastSteps", {
      data: '["Reached returns area" | "Identified 3 packages" | "Picked package 14"]',
    });
    this.store.set("taskQueue", {
      data: '["Place package 14 on rack B02" | "Return for package 15" | "Update inventory log"]',
    });

    const every = (ms: number, fn: () => void) => {
      fn();
      this.timers.push(window.setInterval(fn, ms));
    };

    every(2000, () => this.store.set("heartbeat", { stamp: { sec: 0, nanosec: 0 }, frame_id: "" }));

    every(1200, () => {
      const t = performance.now();
      const wig = (base: number, amp: number, ph: number) =>
        Math.max(0, Math.min(100, base + Math.sin(t / 900 + ph) * amp + (Math.random() - 0.5) * 4));
      this.store.set("utilization", {
        component_names: ["cpu", "ram", "gpu", "disk", "vram"],
        component_values: [wig(46, 18, 0), wig(63, 8, 1), wig(72, 20, 2), 94, wig(58, 14, 3)],
        nav2_state: true,
        moveit2_state: true,
      });
    });

    every(3200, () => {
      this.store.set("plan", buildPath(performance.now()));
    });

    every(4500, () => {
      const a = ACTIONS[this.actionIdx % ACTIONS.length];
      this.actionIdx++;
      this.store.set("currentAction", { text: a, communication_id: String(this.actionIdx) });
    });

    every(6000, () => {
      const v = VLM_LINES[this.vlmIdx % VLM_LINES.length];
      this.vlmIdx++;
      this.store.set("vlm", { image: { height: 0, width: 0, encoding: "", data: [] }, ...v });
    });

    every(3500, () => {
      const e = ROSOUT[this.rosoutIdx % ROSOUT.length];
      this.rosoutIdx++;
      this.store.set("rosout", { ...e, function: "demo" });
    });
  }

  nextRack(): string {
    const rack = ["J01", "B02", "C03", "A04"][this.rackIdx % 4];
    this.rackIdx++;
    return rack;
  }

  stop() {
    this.timers.forEach((t) => window.clearInterval(t));
    this.timers = [];
  }

  elapsed() {
    return performance.now() - this.started;
  }
}
