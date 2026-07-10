# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Developed by Robotec.ai sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import csv
import random
import time
from typing import Literal, Optional

import numpy as np
import pandas as pd
from geometry_msgs.msg import Point, Pose
from rai.agents import BaseAgent, wait_for_shutdown
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
    ROS2Message,
    wait_for_ros2_services,
)
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from simulation_interfaces.msg import EntityState
from std_srvs.srv import Trigger
from tf_transformations import euler_from_quaternion, quaternion_from_euler
from tqdm import tqdm

from rai_app.environment.layout import (
    FireExtinguisherPositions,
    Layout,
)
from rai_app.environment.scene_manager import SceneManager

layout = Layout()

entities_dtype = Literal["box", "barrel", "can", "bucket"]


def load_spawn_config(spawn_config_file):
    """
    Load spawn configuration from CSV file.
    Expected CSV format with headers: slot_name, entity_type
    """
    spawn_slot_names = []
    spawn_entity_types = []
    items_stored = []

    with open(spawn_config_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            spawn_slot_names.append(row["slot_name"])
            spawn_entity_types.append(row["entity_type"])
            items_stored.append(row["item"])

    return spawn_slot_names, spawn_entity_types, items_stored


def load_rack_assignment(rack_assignment_file: str):
    rack_assignment = pd.read_csv(rack_assignment_file, delimiter=",")
    collection_names, item_types = (
        rack_assignment["collection_name"].tolist(),
        rack_assignment["item_type"].tolist(),
    )
    return collection_names, item_types


class SceneManagerState(SceneManager):
    def __init__(
        self,
        slots_file: str,
        spawnables_file: str,
        connector: ROS2Connector | None = None,
        rack_assignment_file: str = "scripts/resources/rack_assignment.csv",
        item_type_assets_file: str = "scripts/resources/item_type_assets.csv",
        tables_spawn_file: str = "scripts/resources/spawn_config_table.csv",
        rack_fill: float = 0.8,
    ):
        super().__init__(
            slots_file=slots_file, spawnables_file=spawnables_file, connector=connector
        )
        self.slots_file = slots_file
        self.spawnables_file = spawnables_file
        self.rack_assignment_file = rack_assignment_file
        self.rack_fill = rack_fill
        self.item_type_assets_file = item_type_assets_file
        self.tables_spawn_file = tables_spawn_file
        wait_for_ros2_services(
            self.connector, ["/spawn_entity", "/delete_entity", "/get_entities"]
        )

        self.safety_positions = [
            (
                "towers_top_of_right_bottom_rack",
                layout.get_top_end_of_the_right_bottom_rack,
            ),
            (
                "towers_end_of_racks",
                layout.get_right_end_of_left_racks,
            ),
            (
                "towers_right_side_of_left_rectangle",
                layout.get_bottom_left_rectangle_2,
            ),
        ]

    def spawn_fire_extinguishers(self):
        entity_type = "fireextinguisher01"
        positions = dict(
            pillars=[
                FireExtinguisherPositions.PILLAR2,
                FireExtinguisherPositions.PILLAR3,
            ],
            top_wall=[
                FireExtinguisherPositions.TOP_WALL,
            ],
            right_wall=[
                FireExtinguisherPositions.RIGHT_WALL,
                FireExtinguisherPositions.RIGHT_WALL2,
            ],
            bottom_wall=[
                FireExtinguisherPositions.BOTTOM_WALL,
            ],
            left_wall=[
                FireExtinguisherPositions.LEFT_WALL,
            ],
        )

        for location, positions in positions.items():
            for position in positions:
                pose = position.to_pose()
                entity_name = self.spawn_object(pose, entity_type)
                print(f"Spawned {entity_name} at {location}")

    def get_boxes(self, box_types: str | list[Literal["O", "T", "D", "G", "all"]]):
        entities = self.get_entities(name_filter="cardboardbox")

        if "all" in box_types:
            return entities

        selected_entities = []
        for box_type in box_types:
            if box_type == "O":
                selected_entities.extend(
                    [entity for entity in entities if entity.endswith("O")]
                )
            if box_type == "T":
                selected_entities.extend(
                    [entity for entity in entities if entity.endswith("T")]
                )
            if box_type == "D":
                selected_entities.extend(
                    [entity for entity in entities if entity.endswith("D")]
                )
            if box_type == "G":
                selected_entities.extend(
                    [
                        entity
                        for entity in entities
                        if not entity.endswith("O")
                        and not entity.endswith("T")
                        and not entity.endswith("D")
                    ]
                )
        return selected_entities

    def get_z_spacing(self, object_type: entities_dtype):
        return {
            "box": 0.25,
            "barrel": 1.2,
            "can": 0.3,
            "bucket": 0.4,
        }[object_type]

    def get_y_spacing(self, object_type: entities_dtype):
        return {
            "box": 0.35,
            "barrel": 0.8,
            "can": 0.3,
            "bucket": 0.45,
        }[object_type]

    def get_max_tower(self, object_type: entities_dtype):
        return {
            "box": 3,
            "barrel": 2,
            "can": 3,
            "bucket": 2,
        }[object_type]

    def fill_scene(
        self,
        clear=True,
        entity_types: list[str] | None = None,
        skip_slots: list[str] | None = None,
        fraction_of_slots: int | None = None,
    ):
        if clear:
            self.clear_scene()

        if entity_types is None:
            entity_types = self.get_boxes("GDO")
        all_slot_names = []

        empty_slots = (
            self.find_empty_slots_on_racks() | self.find_empty_slots_on_tables()
        )

        # Select 1/x of all slots randomly
        if fraction_of_slots:
            empty_slots = {
                rack: random.sample(slots, max(1, int(len(slots) / fraction_of_slots)))
                for rack, slots in empty_slots.items()
            }

        for rack in empty_slots:
            for slot in empty_slots[rack]:
                all_slot_names.append(slot.tag)

        if skip_slots is not None:
            all_slot_names = [
                slot
                for slot in all_slot_names
                if all(s not in slot for s in skip_slots)
            ]

        spawn_slot_names = all_slot_names
        spawn_entity_types = [
            entity_types[i % len(entity_types)] for i in range(len(spawn_slot_names))
        ]

        self.populate_scene(
            spawn_slot_names, spawn_entity_types, std_xy=0.01, std_yaw=0.08
        )

    def spawn_objects_in_towers(
        self,
        entity_type: str,
        positions,
        z_spacing,
        tower_height=5,
    ):
        for position in positions:
            x = position[0] + random.uniform(-0.05, 0.05)
            y = position[1] + random.uniform(-0.05, 0.05)

            print(f"Z spacing for {entity_type}: {z_spacing}")
            heights = np.arange(0.01, tower_height * z_spacing, z_spacing)
            for i, z in enumerate(heights):
                point = Point(x=x, y=y, z=z)
                pose = Pose(position=point)
                self.spawn_object(pose, entity_type)
                if i > 3:
                    time.sleep(0.5)

    def towers_of_objects(
        self,
        max_tower=6,
    ):
        pos = random.choice(self.safety_positions)
        # do not spawn on the same spot twice
        self.safety_positions.remove(pos)
        available_types = [
            "plasticbarrel1",
        ]
        ent_type = random.choice(available_types)
        if "barrel" in ent_type:
            general_type = "barrel"

        z_spacing = self.get_z_spacing(general_type)
        distance_between = self.get_y_spacing(general_type)
        max_tower = self.get_max_tower(general_type)
        print(f"Spawning {ent_type} in {pos[0]}")
        self.spawn_objects_in_towers(
            ent_type,
            pos[1](distance_between),
            z_spacing,
            max_tower,
        )

    def get_standard_objects_to_spawn(self, rack_fill: float):
        spawnables = pd.read_csv(self.spawnables_file, delimiter=",")
        spawnables = spawnables[spawnables["object_name"].str.contains("cardboardbox")]

        collection_names, item_types = load_rack_assignment(self.rack_assignment_file)
        item_type_assets = pd.read_csv(self.item_type_assets_file, delimiter=",")
        item_type_assets["asset_names"] = item_type_assets["asset_names"].str.split(";")

        spawn_slot_names = []
        spawn_entity_types = []
        items_stored = []
        for rack, item_type in zip(collection_names, item_types):
            slots_of_rack = self.get_collection(rack).get_all_slots().values()
            for slot in slots_of_rack:
                if random.random() > rack_fill:
                    continue
                spawn_slot_names.append(slot.tag)
                spawn_entity_types.append(
                    random.choice(
                        item_type_assets.loc[
                            item_type_assets["item_type"] == item_type, "asset_names"
                        ].values[0]
                    )
                )
                items_stored.append(item_type)

        if items_stored is None:
            items_stored = [None] * len(spawn_slot_names)

        if len(spawn_slot_names) != len(items_stored):
            raise ValueError(
                "Slots and object names must have the same length and items stored"
            )
        return spawn_slot_names, spawn_entity_types, items_stored

    def get_returns_table_objects_to_spawn(self):
        return load_spawn_config(self.tables_spawn_file)

    def housekeep_scenario(self, request: Trigger.Request, response: Trigger.Response):
        spawn_slot_names, spawn_entity_types, items_stored = (
            self.get_standard_objects_to_spawn(rack_fill=self.rack_fill)
        )

        self.populate_scene(
            spawn_slot_names,
            spawn_entity_types,
            items_stored,
            std_xy=0.01,
            std_yaw=0.05,
            percent_of_rotated_objects=0.15,
        )

        spawn_slot_names, spawn_entity_types, items_stored = (
            self.get_returns_table_objects_to_spawn()
        )
        self.populate_scene(
            spawn_slot_names,
            spawn_entity_types,
            items_stored,
            std_yaw=0.1,
            offset_yaw=3.14,
        )
        self.spawn_fire_extinguishers()
        return Trigger.Response(success=True)

    def standard_scenario(self, request: Trigger.Request, response: Trigger.Response):
        spawn_slot_names, spawn_entity_types, items_stored = (
            self.get_standard_objects_to_spawn(rack_fill=self.rack_fill)
        )

        self.populate_scene(
            spawn_slot_names,
            spawn_entity_types,
            items_stored,
            std_xy=0.01,
            std_yaw=0.05,
            percent_of_rotated_objects=0.03,
        )

        spawn_slot_names, spawn_entity_types, items_stored = (
            self.get_returns_table_objects_to_spawn()
        )
        self.populate_scene(
            spawn_slot_names,
            spawn_entity_types,
            items_stored,
            std_yaw=0.1,
            offset_yaw=3.14,
        )
        self.spawn_fire_extinguishers()
        return Trigger.Response(success=True)

    def knock_object(self, object_name: str):
        noise = random.uniform(-0.5, 0.5)
        self.move_entity(
            object_name, dx=0.0, dy=0.0, dz=0.1, az=0.0, ay=0.0, ax=-8.0 + noise
        )

    def get_anomaly_entities_states(self) -> dict[str, EntityState] | None:
        all_entities = self.get_entities(name_filter="__anomaly__")
        return {
            entity_name: entity_state
            for entity_name, entity_state in all_entities.items()
            if "GrippingPoint" not in entity_name
        }

    def clear_anomalies(self, request: Trigger.Request, response: Trigger.Response):
        all_entities = self.get_entities(name_filter="__anomaly__")
        for entity_name in all_entities.keys():
            self.delete_entity(entity_name)

    def delete_entity(self, entity_name: str):
        self.connector.call_service(
            ROS2Message(payload={"entity": entity_name}),
            target="/delete_entity",
            msg_type="simulation_interfaces/srv/DeleteEntity",
            timeout_sec=3.0,
        )

    def anomalies(self, request: Trigger.Request, response: Trigger.Response):
        n = 3
        spawning_points = [
            (7.20, 7.44, 0.01, 0.0, 0.0, 0.0, 1.0),
            (2.48, 2.70, 0.00, 0.0, 0.0, 0.0, 1.0),
            (11.29, 3.14, 0.01, 0.0, 0.0, 0.0, 1.0),
            (17.76, 2.95, 0.01, 0.0, 0.0, 0.0, 1.0),
            (23.38, 7.06, 0.01, 0.0, 0.0, 0.0, 1.0),
            (26.90, 11.55, 0.01, 0.0, 0.0, 0.0, 1.0),
            (27.10, 21.35, 0.01, 0.0, 0.0, 0.0, 1.0),
            (27.05, 27.22, 0.01, 0.0, 0.0, 0.0, 1.0),
            (22.72, 25.47, 0.01, 0.0, 0.0, 0.0, 1.0),
            (17.94, 27.42, 0.01, 0.0, 0.0, 0.0, 1.0),
            (17.94, 20.61, 0.01, 0.0, 0.0, 0.0, 1.0),
            (17.71, 15.09, 0.01, 0.0, 0.0, 0.0, 1.0),
            (12.31, 26.86, 0.01, 0.0, 0.0, 0.0, 1.0),
            (8.64, 26.88, 0.01, 0.0, 0.0, 0.0, 1.0),
            (3.97, 25.58, 0.01, 0.0, 0.0, 0.0, 1.0),
        ]
        anomalies_states = self.get_anomaly_entities_states()
        self.logger.info(f"Existing anomalies: {anomalies_states.keys()}")
        # Filter out points that are too close to existing anomalies
        filtered_points = []
        for point in spawning_points:
            too_close = False
            for anomaly_name, anomaly_state in anomalies_states.items():
                # Calculate distance between point and existing anomaly
                dx = point[0] - anomaly_state.pose.position.x
                dy = point[1] - anomaly_state.pose.position.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < 3.0:
                    too_close = True
                    break
            if not too_close:
                filtered_points.append(point)
        self.logger.info(f"Filtered points: {len(filtered_points)}")
        if len(filtered_points) < n:
            self.logger.warning(
                f"Not enough points to spawn {n} anomalies, spawning {len(filtered_points)} anomalies"
            )
            n = len(filtered_points)

        # Update spawning points to filtered list
        spawning_points = filtered_points

        anomalies_poses = [
            Pose(position=Point(x=point[0], y=point[1], z=point[2]))
            for point in random.sample(spawning_points, n)
        ]

        available_types = [
            "cardboardbox02_v01T",
            "cardboardbox01_v01",
            "fireextinguisher01",
        ]
        anomalies_types = random.sample(available_types, n)

        for pose, anomaly_type in tqdm(
            zip(anomalies_poses, anomalies_types), desc="Spawning anomalies"
        ):
            entity_name = self.spawn_object(
                pose=pose, object_name=anomaly_type, item_stored="anomaly"
            )
            if "plasticbarrel" in entity_name:
                self.knock_object(entity_name)
            print("Spawned anomaly: ", entity_name)

        self.towers_of_objects(max_tower=6)
        return Trigger.Response(success=True)

    def spawn_on_spot(
        self,
        slot_name: str,
        object_name: str,
        item_stored: Optional[str] = None,
        std_xy: float = 0.0,
        std_yaw: float = 0.0,
        rotate_90_degrees: bool = False,
        rotate_90_degrees_percentage: float = 0.1,
        offset_yaw: float = 0.0,
        frame: str = "odom",
    ):
        pose: Pose = copy.deepcopy(self.slots[slot_name].origin_pose)
        # Add Gaussian noise to x, y
        pose.position.x += random.normalvariate(0, std_xy)
        pose.position.y += random.normalvariate(0, std_xy)

        # Convert quaternion -> Euler
        q = pose.orientation
        roll, pitch, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # Add Gaussian noise to yaw
        yaw += random.normalvariate(0, std_yaw)
        if rotate_90_degrees:
            if random.random() < rotate_90_degrees_percentage:
                yaw += random.choice([-np.pi / 2, np.pi / 2])
        yaw += offset_yaw

        # Convert back to quaternion
        q_new = quaternion_from_euler(roll, pitch, yaw)
        pose.orientation.x = q_new[0]
        pose.orientation.y = q_new[1]
        pose.orientation.z = q_new[2]
        pose.orientation.w = q_new[3]

        return self.spawn_object(
            pose=pose, object_name=object_name, item_stored=item_stored, frame=frame
        )


class SceneAgent(BaseAgent):
    def __init__(self, connector: ROS2Connector, scene_manager: SceneManagerState):
        super().__init__()
        self.connector = connector
        self.scene_manager_state = scene_manager
        self.callback_group = MutuallyExclusiveCallbackGroup()

        self.connector.create_service(
            service_type="std_srvs/srv/Trigger",
            service_name="rai/scene/housekeep",
            on_request=self.housekeep,
            callback_group=self.callback_group,
        )
        self.connector.create_service(
            service_type="std_srvs/srv/Trigger",
            service_name="rai/scene/anomalies",
            on_request=self.anomalies,
            callback_group=self.callback_group,
        )
        self.connector.create_service(
            service_type="std_srvs/srv/Trigger",
            service_name="rai/scene/clear_anomalies",
            on_request=self.clear_anomalies,
            callback_group=self.callback_group,
        )
        self.connector.create_service(
            service_type="std_srvs/srv/Trigger",
            service_name="rai/scene/standard",
            on_request=self.standard,
            callback_group=self.callback_group,
        )
        self.connector.create_service(
            service_type="std_srvs/srv/Trigger",
            service_name="rai/scene/cleanup",
            on_request=self.cleanup,
            callback_group=self.callback_group,
        )
        self.logger.info("Scene agent initialized")

    def housekeep(self, request: Trigger.Request, response: Trigger.Response):
        self.logger.info("Request to populate the scene according to housekeep recipe")
        self.scene_manager_state.housekeep_scenario(request, response)
        self.logger.info("Scene populated according to housekeep recipe")
        return Trigger.Response(success=True)

    def clear_anomalies(self, request: Trigger.Request, response: Trigger.Response):
        self.logger.info("Request to clear anomalies")
        self.scene_manager_state.clear_anomalies(request, response)
        self.logger.info("Anomalies cleared")
        return Trigger.Response(success=True)

    def anomalies(self, request: Trigger.Request, response: Trigger.Response):
        self.logger.info("Request to populate the scene according to anomalies recipe")
        self.scene_manager_state.anomalies(request, response)
        self.logger.info("Scene populated according to anomalies recipe")
        return Trigger.Response(success=True)

    def standard(self, request: Trigger.Request, response: Trigger.Response):
        self.logger.info("Request to populate the scene according to standard recipe")
        self.scene_manager_state.standard_scenario(request, response)
        self.logger.info("Scene populated according to standard recipe")
        return Trigger.Response(success=True)

    def cleanup(self, request: Trigger.Request, response: Trigger.Response):
        self.connector.service_call(
            ROS2Message(payload={}),
            target="/reset_simulation",
            msg_type="simulation_interfaces/srv/ResetSimulation",
            timeout_sec=5.0,
        )
        self.safety_positions = [
            (
                "towers_top_of_right_bottom_rack",
                layout.get_top_end_of_the_right_bottom_rack,
            ),
            (
                "towers_end_of_racks",
                layout.get_right_end_of_left_racks,
            ),
            (
                "towers_left_side_of_left_rectangle",
                layout.get_bottom_left_rectangle_2,
            ),
            (
                "towers_right_side_of_left_rectangle",
                layout.get_bottom_left_rectangle_2,
            ),
        ]
        return Trigger.Response(success=True)

    def run(self):
        pass

    def stop(self):
        self.connector.shutdown()


@ROS2Context()
def main():
    connector = ROS2Connector(executor_type="single_threaded")
    scene_manager_state = SceneManagerState(
        connector=connector,
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        rack_assignment_file="scripts/resources/rack_assignment.csv",
        item_type_assets_file="scripts/resources/item_type_assets.csv",
    )
    scene_agent_connector = ROS2Connector(executor_type="single_threaded")
    scene_agent = SceneAgent(scene_agent_connector, scene_manager_state)
    scene_agent.run()
    wait_for_shutdown([scene_agent])


if __name__ == "__main__":
    main()
