# Operating the Demo

This page explains how to drive the demo from the HMI once everything is running.
If the stack is not up yet, start it first. See [Running the demo](./running.md)
for a local run, or the [Quickstart](./quickstart.md) for Docker. Then come back
here.

Populate the scene first, wait for the objects to finish spawning, then start a
mission.

## The HMI at a glance

The left rail switches between four pages; the top bar is always visible:

- **Top bar**: mission state (idle, running, emergency stop), simulation time, how many
  inference endpoints and agents are up, and the **E-STOP** button.
- **Mission** (opens first): type a task or pick a quick task, watch the cameras and
  the map, follow the current task's steps and the queue, and read the **agent
  stream**, where every agent's messages, reasoning, tool calls and findings appear live.
- **Agents**: which agent is working on what, and a **trace** of the current task:
  one row per message, tool call or finding with its timing. Click a row for its full
  content (tool arguments and results, token counts, the finding's image); click an
  agent to show only its rows.
- **Simulation**: scene recipes, task builders and manual driving.
- **System**: CPU, GPU, NPU and RAM, agent heartbeats, inference endpoint health, and
  logs filterable by level and text.

## Step 1: Populate the scene first

Populate the scene with objects before starting a mission. On the **Simulation**
page, click one of the scene recipes:

- **Standard**: the usual starting point. Fills the racks with boxes, places
  return packages on the tables.
- **Housekeeping**: a similar fill recipe.
- **Anomalies**: adds a few out-of-place objects and a stack of barrels, so the
  inspection and safety agents have something to find.
- **Cleanup**: resets the simulation and clears the spawned objects. Use this to
  start over.

The card shows LOADING until the scene agent answers, then LOADED. If the scene agent
is not running, a message at the bottom of the window says so: make sure the agents
are up (see [Running the demo](./running.md)) and try again.

## Step 2: Start a mission

Once the scene is populated, give the robot a mission:

- **Sort returns**: the robot sorts the return packages waiting on the tables based
  on their condition.
- **Housekeeping**: on the **Simulation** page, click the racks to tidy (the number
  shows the order), then **Queue**. One task per rack is queued in that order.
- **Prepare shipment**: on the **Simulation** page, select the items (CPU, GPU,
  motherboard, pipes, hammers, nails), then **Add to queue**.

Sort returns and a few housekeeping racks are also quick tasks on the **Mission**
page. The orchestrator keeps a task queue, so you can add tasks while one runs.

### Custom tasks

Type any task into the box at the top of the **Mission** page and press Enter or
**Assign**. It is published on `/user_tasks`, which you can also use directly:

```bash
ros2 topic pub --once /user_tasks std_msgs/msg/String "data: 'Do Housekeeping of rack J01'"
```

## Monitoring progress

While a mission runs, the **Mission** page shows the robot cameras (base, wrist,
top), the map with the robot and its plan, the steps done so far, the queue, and the
agent stream. Filter the stream by agent with the chips above it; scrolling up stops
it following new entries, **Follow** resumes. **Open trace** jumps to the **Agents**
page for the timing and full content of each step.

The **System** page shows when something is stuck: an agent whose heartbeat stopped,
an inference endpoint that is down, or warnings in the logs.

## Stopping and manual control

- **E-STOP** (top bar, every page): the orchestrator aborts the current task and
  clears the queue, and Nav2 pauses. **Release stop** lets the orchestrator take new
  tasks and resumes Nav2. Tasks sent while stopped wait in the queue.
- **Manual control** (Simulation page): enable it, then drive the base with the pad
  or W A S D (space stops). The agents keep running, so stop the mission first.
- **Navigation goal**: double-click a spot on the map to send the robot there.
