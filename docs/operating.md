# Operating the Demo

This page explains how to drive the demo from the HMI once everything is running.
If the stack is not up yet, start it first (see [Running the demo](./running.md), e.g.
`pixi run demo`), then come back here.

The order of operations matters: you populate the scene first, wait for the
objects to finish spawning, and only then start a mission.

## The HMI at a glance

The HMI window has three tabs:

- **Control**: populate the scene, start missions, emergency stop, manual driving.
- **Status**: system tiles (CPU, GPU, NPU, RAM, Nav2, MoveIt2, agents) and logs.
- **Mission**: the mission observer, robot cameras, the map, the live agent task
  list, and the VLM output.

The window opens on the **Mission** tab. Click over to the **Control** tab to set
things up.

## Step 1: Populate the scene first

Nothing meaningful can happen in an empty warehouse, so the first thing you do is
fill it with objects.

On the **Control** tab, find the **Simulation Scenarios** group and click one of
the scene recipes:

- **Standard**: the usual starting point. Fills the racks with boxes, places
  return packages on the tables.
- **Housekeeping**: a similar fill recipe used for the housekeeping storyline.
- **Anomalies**: adds a few out-of-place objects and a stack of barrels, so the
  inspection and safety agents have something to find.
- **Cleanup**: resets the simulation and clears the spawned objects. Use this to
  start over.

Spawning is not instant. It can take up to about 30 seconds, and you can watch the
objects appear one by one in the O3DE simulation window (or on the top view camera
on the **Mission** tab). Wait until spawning has finished before moving on.

If you click a scene button and get a "Service not available" warning, the scene
agent is not running yet. Make sure the agents are up (they start as part of
`pixi run agents` or `pixi run demo`) and try again.

## Step 2: Start a mission

Once the scene is populated, use the **On Demand prefined tasks** group on the
**Control** tab to give the robot a mission:

- **Sort returns**: the robot sorts the return packages waiting on the tables based on their condition.
- **Housekeeping**: the robot tidies a rack. Each click targets the next rack in sequence, so pressing it repeatedly walks through the warehouse rack by rack.
- **Prepare shipment**: first tick the items you want (CPU, GPU, pipes, hammers,
  nails, motherboard) in the shipment configuration, then click **Prepare
  shipment**. The robot collects the selected items.

The mission is handed to the orchestrator, which breaks it into steps and drives
the robot. You do not need to wait for one mission to fully finish before queueing
another; the orchestrator keeps a task queue.

## Watching what happens

While a mission runs, the **Mission** tab is the place to watch:

- The robot cameras (base and wrist, plus a top view).
- The map, with the robot pose and its current plan.
- The **Agent Task** panel, showing the current action, the current task, and the
  queued and completed steps.
- The VLM output, showing what the vision models report.

The **Status** tab shows live system utilization and the health of Nav2, MoveIt2,
and the agents, which is useful when something looks stuck.

## Stopping and manual control

- **STOP!** on the **Control** tab triggers an emergency stop.
- The **Manual Control** section on the **Control** tab lets you drive the base
  directly with the on-screen teleop buttons.
