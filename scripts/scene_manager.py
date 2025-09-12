import argparse
import random
import uuid
from typing import cast

import pandas as pd
from geometry_msgs.msg import Point, Pose, Quaternion
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_services,
)
from rosidl_runtime_py.convert import message_to_ordereddict
from simulation_interfaces.srv import (
    GetEntities,
    GetEntityState,
    SetEntityState,
    SpawnEntity,
)
from tf2_geometry_msgs import do_transform_pose
from tf_transformations import euler_from_quaternion, quaternion_from_euler
from tqdm import tqdm


class SceneManager:
    def __init__(self, slots_file: str, spawnables_file: str):
        self.connector = ROS2Connector(
            executor_type="single_threaded", node_name="scene_manager"
        )
        self.logger = self.connector.node.get_logger()

        self.slot_to_pose = {}

        df = pd.read_csv(slots_file, delimiter=",")
        names = df["slot_name"].tolist()
        positions = df[["x", "y", "z"]].values
        quaternions = df[["qx", "qy", "qz", "qw"]].values
        for slot_name, position, quaternion in zip(names, positions, quaternions):
            self.slot_to_pose[slot_name] = Pose(
                position=Point(x=position[0], y=position[1], z=position[2]),
                orientation=Quaternion(
                    x=quaternion[0], y=quaternion[1], z=quaternion[2], w=quaternion[3]
                ),
            )

        self.spawnable_to_uri: dict[str, str] = {}
        df = pd.read_csv(spawnables_file, delimiter=",")
        names = df["object_name"].tolist()
        uris = df["uri"].tolist()
        for name, uri in zip(names, uris):
            self.spawnable_to_uri[name] = uri

    def _get_pose(self, entity_name, frame="odom"):
        entity_state = self.connector.call_service(
            ROS2Message(payload={"entity": entity_name}),
            target="/get_entity_state",
            msg_type="simulation_interfaces/srv/GetEntityState",
            timeout_sec=3.0,
        ).payload
        entity_state = cast(GetEntityState.Response, entity_state).result
        return do_transform_pose(
            entity_state.pose,
            self.connector.get_transform(frame, "odom"),
        )

    def get_slot_pose(self, slot_name: str, frame: str = "odom"):
        if frame != "odom":
            raise NotImplementedError("Only odom frame is supported")
        return self.slot_to_pose[slot_name]

    def get_gripping_point(self, unique_object_name: str):
        entity_state = GetEntityState.Request()
        entity_state.entity = unique_object_name + "_GrippingPoint"
        pose = self._get_pose(entity_state.entity)
        return pose

    def populate_scene(
        self,
        slots: list[str],
        object_names: list[str],
        std_xy: float = 0.0,
        std_yaw: float = 0.0,
    ):
        if len(slots) != len(object_names):
            raise ValueError("Slots and object names must have the same length")
        self.logger.info(f"Populating scene with {len(slots)} entities")
        simulation_names: list[str] = []
        for slot, object_name in tqdm(
            zip(slots, object_names), desc="Spawning entities", total=len(slots)
        ):
            simulation_name = self.spawn_on_spot(slot, object_name, std_xy, std_yaw)
            simulation_names.append(simulation_name)
        return simulation_names

    def spawn_on_spot(
        self,
        slot_name: str,
        object_name: str,
        std_xy: float = 0.0,
        std_yaw: float = 0.0,
        frame: str = "odom",
    ):
        wait_for_ros2_services(self.connector, ["/spawn_entity"])
        pose: Pose = self.slot_to_pose[slot_name]

        # Add Gaussian noise to x, y
        pose.position.x += random.normalvariate(0, std_xy)
        pose.position.y += random.normalvariate(0, std_xy)

        # Convert quaternion -> Euler
        q = pose.orientation
        roll, pitch, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # Add Gaussian noise to yaw
        yaw += random.normalvariate(0, std_yaw)

        # Convert back to quaternion
        q_new = quaternion_from_euler(roll, pitch, yaw)
        pose.orientation.x = q_new[0]
        pose.orientation.y = q_new[1]
        pose.orientation.z = q_new[2]
        pose.orientation.w = q_new[3]

        name = object_name + str(uuid.uuid4())[:8]

        req = SpawnEntity.Request()
        req.name = name
        req.uri = self.spawnable_to_uri[object_name]
        req.initial_pose.header.frame_id = frame
        req.initial_pose.pose.position.x = pose.position.x
        req.initial_pose.pose.position.y = pose.position.y
        req.initial_pose.pose.position.z = pose.position.z
        req.initial_pose.pose.orientation.x = pose.orientation.x
        req.initial_pose.pose.orientation.y = pose.orientation.y
        req.initial_pose.pose.orientation.z = pose.orientation.z
        req.initial_pose.pose.orientation.w = pose.orientation.w

        self.logger.debug(f"Spawning {name}")
        result = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req)),
            target="/spawn_entity",
            msg_type="simulation_interfaces/srv/SpawnEntity",
            timeout_sec=3.0,
            reuse_client=True,
        ).payload
        result = cast(SpawnEntity.Response, result)
        return name

    def clear_scene(self):
        self.logger.info("Clearing spawnable entities")
        wait_for_ros2_services(self.connector, ["/get_entities", "/delete_entity"])
        response = self.connector.call_service(
            ROS2Message(payload={}),
            target="/get_entities",
            msg_type="simulation_interfaces/srv/GetEntities",
            timeout_sec=3.0,
        )
        entities = cast(GetEntities.Response, response.payload)
        for entity in tqdm(
            entities.entities, desc="Deleting entities", total=len(entities.entities)
        ):
            self.logger.debug(f"Deleting {entity}")
            self.connector.call_service(
                ROS2Message(payload={"entity": entity}),
                target="/delete_entity",
                msg_type="simulation_interfaces/srv/DeleteEntity",
                timeout_sec=3.0,
            )

    def move_entity(self, entity_name, x=0.0, y=0.0, z=0.0, sx=0.0, sy=0.0, sz=0.0):
        wait_for_ros2_services(
            self.connector, ["/get_entity_state", "/set_entity_state"]
        )

        req_get = GetEntityState.Request()
        req_get.entity = entity_name
        response = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req_get)),
            target="/get_entity_state",
            msg_type="simulation_interfaces/srv/GetEntityState",
            timeout_sec=3.0,
        ).payload
        entity_state = cast(GetEntityState.Response, response).result

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

        result = self.connector.call_service(
            ROS2Message(payload=message_to_ordereddict(req)),
            target="/set_entity_state",
            msg_type="simulation_interfaces/srv/SetEntityState",
            timeout_sec=3.0,
        ).payload
        future = cast(SetEntityState.Response, result).result

        if future.result() is not None:
            print(f"Move result: {future.result}")
        else:
            self.logger.error(f"Service call failed: {future.exception()}")


@ROS2Context()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--spawn", action="store_true", default=True)
    parser.add_argument("--slots-file", type=str, default="scripts/resources/slots.csv")
    parser.add_argument(
        "--spawnables-file", type=str, default="scripts/resources/spawnables.csv"
    )
    parser.add_argument("--filter", type=str, default="ego|oilspill1|oilspill2")
    args = parser.parse_args()

    scene_manager = SceneManager(
        slots_file=args.slots_file, spawnables_file=args.spawnables_file
    )

    slots = pd.read_csv(args.slots_file, delimiter=",")
    spawnables = pd.read_csv(args.spawnables_file, delimiter=",")
    spawnables = spawnables[~spawnables["object_name"].isin(args.filter.split("|"))]
    object_names = [
        random.choice(list(spawnables["object_name"].tolist()))
        for _ in range(len(slots))
    ]

    slot_names = slots["slot_name"].tolist()

    if args.spawn:
        scene_manager.populate_scene(slot_names, object_names)

    if args.clear:
        scene_manager.clear_scene()

    scene_manager.connector.shutdown()


if __name__ == "__main__":
    main()
