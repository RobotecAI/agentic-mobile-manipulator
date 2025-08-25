#!/usr/bin/env python3

import csv
import time
from io import StringIO

import rclpy
from simulation_interfaces.srv import (
    DeleteEntity,
    GetEntities,
    GetEntityState,
    ResetSimulation,
    SetEntityState,
    SpawnEntity,
)

spawnables = {
    "ego": "product_asset:///assets/rbkairos_plus.spawnable",
    "cardboardbox01": "product_asset:///assets/payload/boxes/cardboardbox01.spawnable",
    "cardboardbox02": "product_asset:///assets/payload/boxes/cardboardbox02.spawnable",
    "cardboardboxdamaged01": "product_asset:///assets/payload/boxes/cardboardboxdamaged01.spawnable",
    "cardboardboxdamaged02": "product_asset:///assets/payload/boxes/cardboardboxdamaged02.spawnable",
    "oilspill1": "product_asset:///assets/payload/oilspills/oilspill1.spawnable",
    "oilspill2": "product_asset:///assets/payload/oilspills/oilspill2.spawnable",
}

# Poses for boxes - x,y,z,qx,qy,qz,qw
# those poses are published on topic /sim/poses
# Recommened waty ot get it is via cli:
# ros2 topic echo /sim/reported_points --qos-history keep_all --qos-depth 1000 --csv
poses_raw = """
RackSlot2,[129235007734410],23.737,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129239302701706],24.771,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129243597669002],25.754,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129256482570890],27.013,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129260777538186],14.728,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129265072505482],15.761,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129269367472778],16.745,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129282252374666],18.003,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129286547341962],10.224,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129290842309258],11.258,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129295137276554],12.241,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129308022178442],13.500,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129312317145738],5.718,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129316612113034],6.751,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129320907080330],7.735,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129333791982218],8.994,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129338086949514],19.234,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129342381916810],20.268,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129346676884106],21.251,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129359561785994],22.510,29.749,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129363856753290],5.416,5.000,0.850,0.000,0.000,0.707,0.707
AnomalySlot2,[129368151720586],6.449,5.000,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129372446687882],7.433,5.000,0.850,0.000,0.000,0.707,0.707
AnomalySlot1,[129385331589770],8.691,5.000,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129389626557066],20.000,6.584,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129393921524362],20.000,5.551,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129398216491658],20.000,4.567,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129411101393546],20.000,3.309,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129415396360842],23.737,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129419691328138],24.771,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129423986295434],25.754,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129436871197322],27.013,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129441166164618],14.728,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129445461131914],15.761,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129449756099210],16.745,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129462641001098],18.003,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129466935968394],19.234,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129471230935690],20.268,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129475525902986],21.251,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129488410804874],22.510,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129492705772170],10.224,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129497000739466],11.258,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129501295706762],12.241,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129514180608650],13.500,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129518475575946],5.718,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129522770543242],6.751,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129527065510538],7.735,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129539950412426],8.994,0.704,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129544245379722],5.416,25.000,0.850,0.000,0.000,0.707,0.707
RackSlot1,[129548540347018],6.449,25.000,0.850,0.000,0.000,0.707,0.707
RackSlot3,[129552835314314],7.433,25.000,0.850,0.000,0.000,0.707,0.707
RackSlot4,[129565720216202],8.691,25.000,0.850,0.000,0.000,0.707,0.707
RackSlot2,[129570015183498],25.000,6.584,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129574310150794],25.000,5.551,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129578605118090],25.000,4.567,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129591490019978],25.000,3.309,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129595784987274],25.000,21.090,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129600079954570],25.000,20.057,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129604374921866],25.000,19.074,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129617259823754],25.000,17.815,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129621554791050],25.000,25.600,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129625849758346],25.000,24.567,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129630144725642],25.000,23.583,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129643029627530],25.000,22.325,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129647324594826],29.219,23.886,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129651619562122],29.219,22.853,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129655914529418],29.219,21.869,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129668799431306],29.219,20.610,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129673094398602],29.219,9.731,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129677389365898],29.219,8.698,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129681684333194],29.219,7.714,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129694569235082],29.219,6.455,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129698864202378],29.219,19.379,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129703159169674],29.219,18.345,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129707454136970],29.219,17.362,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129720339038858],29.219,16.103,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129724634006154],29.219,28.391,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129728928973450],29.219,27.357,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129733223940746],29.219,26.374,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129746108842634],29.219,25.115,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129750403809930],29.219,5.225,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129754698777226],29.219,4.192,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129758993744522],29.219,3.208,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129771878646410],29.219,1.950,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129776173613706],29.219,14.232,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129780468581002],29.219,13.198,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129784763548298],29.219,12.215,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129797648450186],29.219,10.956,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129801943417482],20.000,21.090,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129806238384778],20.000,20.057,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129810533352074],20.000,19.074,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129823418253962],20.000,17.815,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129827713221258],20.000,25.600,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129832008188554],20.000,24.567,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129836303155850],20.000,23.583,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129849188057738],20.000,22.325,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129853483025034],15.000,25.600,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129857777992330],15.000,24.567,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129862072959626],15.000,23.583,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129874957861514],15.000,22.325,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129879252828810],15.000,21.090,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129883547796106],15.000,20.057,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129887842763402],15.000,19.074,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129900727665290],15.000,17.815,0.850,0.000,0.000,0.000,1.000
RackSlot2,[129905022632586],15.000,6.584,0.850,0.000,0.000,0.000,1.000
RackSlot1,[129909317599882],15.000,5.551,0.850,0.000,0.000,0.000,1.000
RackSlot3,[129913612567178],15.000,4.567,0.850,0.000,0.000,0.000,1.000
RackSlot4,[129926497469066],15.000,3.309,0.850,0.000,0.000,0.000,1.000
"""


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
    x=0.0,
    y=0.0,
    z=0.0,
    qx=0.0,
    qy=0.0,
    qz=0.0,
    qw=1.0,
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
    req.initial_pose.pose.orientation.x = qx
    req.initial_pose.pose.orientation.y = qy
    req.initial_pose.pose.orientation.z = qz
    req.initial_pose.pose.orientation.w = qw

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
    poses = []
    reader = csv.reader(StringIO(poses_raw))
    for row in reader:
        if len(row) == 0:
            continue
        name = row[0]
        x, y, z, qx, qy, qz, qw = map(float, row[2:])
        poses.append([name, x, y, z, qx, qy, qz, qw])

    rclpy.init()

    node = rclpy.create_node("spawnables_client")
    ResetSim(node)

    for i, poseData in enumerate(poses):
        slotName, x, y, z, qx, qy, qz, qw = poseData
        objectType = "cardboardbox01"
        Spawn(node, objectType, f"{slotName}_{i}", x, y, z, qx, qy, qz, qw)

    # Find anomaly boxes
    time.sleep(1)
    client = node.create_client(GetEntities, "get_entities")
    if not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service get_entity_state not available, waiting...")
        return
    req = GetEntities.Request()
    req.filters.filter = "^AnomalySlot.*"
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)

    anomaly_entities_names = []
    if future.result() is not None:
        anomaly_entities_names = future.result().entities
        print(f"Anomaly entities: {anomaly_entities_names}")

    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")
        return

    if len(anomaly_entities_names) < 2:
        node.get_logger().error("Not enough anomaly entities found!")
        return

    # Make first anomaly - make box fall down
    anomaly1 = anomaly_entities_names[0]
    MoveEntity(node, anomaly1, sx=5.0)

    # Make second anomaly - replace box with damaged box
    anomaly2 = anomaly_entities_names[1]

    # get position of the anomaly2 entity
    client_getState = node.create_client(GetEntityState, "get_entity_state")
    if not client_getState.wait_for_service(timeout_sec=1.0):
        node.get_logger().error("Service get_entity_state not available, waiting...")
        return
    req_get = GetEntityState.Request()
    req_get.entity = anomaly2
    future_get = client_getState.call_async(req_get)
    rclpy.spin_until_future_complete(node, future_get)
    if future_get.result() is not None:
        entity_state = future_get.result()
    else:
        node.get_logger().error(f"Service call failed: {future_get.exception()}")
        return

    # delete the anomaly2 entity
    ClearSpawnedEntities(node, anomaly2)

    # spawn a damaged box at the same position
    Spawn(
        node,
        "cardboardboxdamaged01",
        anomaly2,
        x=entity_state.state.pose.position.x,
        y=entity_state.state.pose.position.y,
        z=entity_state.state.pose.position.z,
        qx=entity_state.state.pose.orientation.x,
        qy=entity_state.state.pose.orientation.y,
        qz=entity_state.state.pose.orientation.z,
        qw=entity_state.state.pose.orientation.w,
        frame_id="world",
    )

    # Make thirrd anomaly - oil spill next to robot
    Spawn(
        node,
        "oilspill1",
        "ANOMALY_OilSpill1",
        x=6.24,
        y=6.98,
        z=0.0,
        qx=0.0,
        qy=0.0,
        qz=0.707,
        qw=0.707,
        frame_id="odom",
    )

    Spawn(
        node,
        "oilspill2",
        "ANOMALY_OilSpill2",
        x=7.24,
        y=6.98,
        z=0.0,
        qx=0.0,
        qy=0.0,
        qz=0.707,
        qw=0.707,
        frame_id="odom",
    )


if __name__ == "__main__":
    main()
