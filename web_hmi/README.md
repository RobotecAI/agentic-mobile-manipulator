# Kairos+ Web HMI

A cinematic, browser-based Human-Machine-Interface for the Robotnik Kairos+
agentic mobile manipulator — a design-forward alternative to the native Qt HMI.

It talks to the live ROS 2 stack over **rosbridge** (WebSocket) and streams
camera feeds via **web_video_server**, and ships a built-in **demo mode** so the
whole UI is alive without any ROS running.

|                |                                                                               |
| -------------- | ----------------------------------------------------------------------------- |
| **Stack**      | Vite 6 · React 19 · TypeScript · Tailwind CSS v4 · Motion · lucide            |
| **ROS bridge** | [`roslib`](https://github.com/RobotWebTools/roslibjs) over `rosbridge_server` |
| **Video**      | `web_video_server` MJPEG streams                                              |

## Develop

```bash
cd web_hmi
npm install
npm run dev        # http://localhost:5173
```

Open `http://localhost:5173/?demo=1` to force the synthetic feed (no ROS needed).

## Build

```bash
npm run build      # -> dist/  (static, host anywhere)
npm run preview
```

## Try it with mock ROS 2 data

To exercise the **real** rosbridge path (not the in-browser demo), a mock
backend publishes every topic, serves the scenario services, and _reacts_ to
what the GUI sends (a free-form command updates the current task; E-STOP halts
the agent):

```bash
# terminal 1 — rosbridge + (optional) web_video_server + mock publisher
./web_hmi/tools/run_mock_stack.sh

# terminal 2 — the UI
cd web_hmi && npm run dev      # http://localhost:5173  (no ?demo flag)
```

The header chip should flip to **rosbridge · live** and **agent online**; gauges,
the map/plan, agent stream and VLM feed all update live. Type a command in the
Control tab and watch it round-trip through ROS into the Mission tab.

`mock_ros_publisher.py` can also be run on its own (`python3 web_hmi/tools/mock_ros_publisher.py`) alongside any rosbridge instance.

## Connecting to ROS 2

On the robot / sim machine:

```bash
# bridge topics & services to the browser
ros2 launch rosbridge_server rosbridge_websocket_launch.xml      # ws://<host>:9090
# expose camera image topics as MJPEG
ros2 run web_video_server web_video_server                       # http://<host>:8080
```

The HMI auto-connects to `ws://<current-host>:9090`. If rosbridge does not
answer within a couple of seconds it falls back to the demo feed.

### Configuration

Override endpoints via query string, `localStorage` (`hmi.*`), or `VITE_*` env:

| Setting       | Query param                     | Env              | Default              |
| ------------- | ------------------------------- | ---------------- | -------------------- |
| rosbridge URL | `?rosbridge=ws://host:9090`     | `VITE_ROSBRIDGE` | `ws://<host>:9090`   |
| video server  | `?video=http://host:8080`       | `VITE_VIDEO`     | `http://<host>:8080` |
| force demo    | `?demo=1`                       | `VITE_DEMO=1`    | off                  |
| initial tab   | `?tab=mission\|control\|status` | —                | `mission`            |

## ROS interfaces

All interface names live in [`src/ros/config.ts`](src/ros/config.ts) and mirror
the native HMI. Subscribed: `/utilization`, `/vlm_topic`, `/rosout`,
`/agent/current_action`, `/orchestrator/{current_task,tasks_queue,paused_tasks,heartbeat}`,
`/agent/past_steps`, `/global_costmap/static_layer`, `/plan`. Published:
`/cmd_vel`, `/goal_pose`, `/emergency_stop`, `/user_tasks`. Services
(`std_srvs/Trigger`): `/restart`, `/rai/scene/{standard,housekeep,anomalies,cleanup}`.

## Layout

- `src/ros/` — connection provider, typed hooks (`useTopic`, `useTopicLog`,
  `useTopicSeries`), message types, and the demo engine.
- `src/components/` — header, glass UI kit (gauges, sparklines, orbs), map &
  camera renderers.
- `src/tabs/` — **Mission** (viewport + agent stream + VLM), **Control**
  (natural-language command, missions, scenarios, manual drive), **Telemetry**
  (gauges, inference stack, subsystems, event timeline).
