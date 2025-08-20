#!/usr/bin/env python3

import time

import rclpy
from simulation_interfaces.srv import (
    DeleteEntity,
    GetEntityState,
    ResetSimulation,
    SetEntityState,
    SpawnEntity,
)

spawnables = {
    "carrot": "product_asset:///assets/prefabs/carrot.spawnable",
    "corn": "product_asset:///assets/prefabs/corn.spawnable",
    "green_cube": "product_asset:///assets/prefabs/green_cube.spawnable",
    "ego": "product_asset:///assets/rbkairos_plus.spawnable",
}


### Move an entity in the simulation
### This is used to move the ToyBoxContainer entity in the simulation
### parameters:
### - node: the ROS2 node
### - entity_name: the name of the entity to move
### - x, y, z: the position to move the entity to (relative to its current position)
### - sx, sy, sz: the linear velocity to set for the entity
def MoveEntity(node, entity_name, x=0.0, y=0.0, z=0.0, sx=0.0, sy=0.0, sz=0.0):
    client_getState = node.create_client(GetEntityState, "get_entity_state")
    client_setState = node.create_client(SetEntityState, "set_entity_state")

    if not client_setState.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service not available, waiting...")
        return
    if not client_getState.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service get_entity_state not available, waiting...")
        return

    # get state of the entity
    req_get = GetEntityState.Request()
    req_get.entity = entity_name
    future_get = client_getState.call_async(req_get)
    rclpy.spin_until_future_complete(node, future_get)
    if future_get.result() is not None:
        entity_state = future_get.result()
        print(f"Entity state: {entity_state}")
    else:
        node.get_logger().error(f"Service call failed: {future_get.exception()}")
        return

    req = SetEntityState.Request()
    req.entity = entity_name  # Entity name in simulation
    req.state.pose.position.x = entity_state.state.pose.position.x + x
    req.state.pose.position.y = entity_state.state.pose.position.y + y
    req.state.pose.position.z = entity_state.state.pose.position.z + z
    req.state.pose.orientation.x = entity_state.state.pose.orientation.x
    req.state.pose.orientation.y = entity_state.state.pose.orientation.y
    req.state.pose.orientation.z = entity_state.state.pose.orientation.z
    req.state.pose.orientation.w = entity_state.state.pose.orientation.w
    req.state.twist.linear.x = sx
    req.state.twist.linear.y = sy
    req.state.twist.linear.z = sz
    req.state.twist.angular.x = 0.0
    req.state.twist.angular.y = 0.0
    req.state.twist.angular.z = 0.0
    req.state.header.frame_id = entity_state.state.header.frame_id

    future = client_setState.call_async(req)
    rclpy.spin_until_future_complete(node, future)

    if future.result() is not None:
        print(f"Move result: {future.result().result}")
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")


def ResetSim(node):
    client = node.create_client(ResetSimulation, "reset_simulation")
    while not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().info("Service reset_simulation not available, waiting...")

    req = ResetSimulation.Request()
    req.scope = (
        ResetSimulation.Request.SCOPE_SPAWNED
    )  # Reset everything in the simulation
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)
    if future.result() is not None:
        node.get_logger().info(f"Reset result: {future.result().result}")
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")


# Spawn a carrot in front of the robot


def Spawn(
    node,
    objectType="carrot",
    name="ANOMALY_Carrot",
    x=1.5,
    y=0.0,
    z=0.2,
    frame_id="egobase_link",
):
    client = node.create_client(SpawnEntity, "spawn_entity")
    if not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service not available, waiting...")
        return
    # spawn a carrot in front of the robot
    req = SpawnEntity.Request()
    req.name = name
    req.uri = spawnables[objectType]
    req.initial_pose.header.frame_id = frame_id
    req.initial_pose.pose.position.x = x
    req.initial_pose.pose.position.y = y
    req.initial_pose.pose.position.z = z
    req.initial_pose.pose.orientation.x = 0.0
    req.initial_pose.pose.orientation.y = 0.0
    req.initial_pose.pose.orientation.z = 0.0
    req.initial_pose.pose.orientation.w = 1.0

    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)

    if future.result() is not None:
        print(f"Spawn result: {future.result().result}")
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")


def ClearSpawnedEntities(node, name="ANOMALY_Carrot"):
    client = node.create_client(DeleteEntity, "delete_entity")
    if not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service not available, waiting...")
        return
    # clear the carrot anomaly
    req = DeleteEntity.Request()
    req.entity = name  # Entity name in simulation
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)
    if future.result() is not None:
        print(f"Clear result: {future.result().result}")
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")


def main():
    rclpy.init()

    node = rclpy.create_node("spawnables_client")
    ResetSim(node)

    for i in range(20):
        Spawn(
            node,
            "carrot",
            f"ANOMALY_GreenCube_{i}",
            x=1.5,
            y=0.0,
            z=0.2 + i * 0.01,
            frame_id="egobase_link",
        )
    time.sleep(5)

    for i in range(20):
        ClearSpawnedEntities(node, f"ANOMALY_GreenCube_{i}")
    time.sleep(2)

    # poke the ToyBoxContainer entity in the simulation
    MoveEntity(node, "ToyBoxContainer", sy=10.0)
    time.sleep(2)
    # move robot to different position
    MoveEntity(node, "egobase_link", x=0.0, y=4.0, z=0.0)
    time.sleep(2)
    MoveEntity(node, "MainDesk", x=0.0, y=1.0, z=0.0)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
