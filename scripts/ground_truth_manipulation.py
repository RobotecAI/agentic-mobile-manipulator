#!/usr/bin/env python3

from kairos_controller import KairosController
from rai.communication.ros2 import ROS2Connector, ROS2Context
from rclpy.impl.logging_severity import LoggingSeverity
from tqdm import tqdm

from scripts.scene_manager import SceneManager


@ROS2Context()
def main(debug: bool = False):
    connector = ROS2Connector(
        executor_type="single_threaded", node_name="ground_truth_manipulation"
    )
    kairos_controller = KairosController(connector=connector)
    if debug:
        kairos_controller.logger.set_level(LoggingSeverity.DEBUG)

    print("KAIROS CONTROLLER INITIALIZED")

    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )

    print("SCENE MANAGER INITIALIZED")
    scene_manager.clear_scene()

    entity_types = [
        "cardboardbox01_v01",
        "cardboardbox01_v02D",
        "cardboardbox01_v03",
        "cardboardbox02_v01",
        "cardboardbox02_v02D",
        "cardboardbox03_v01",
        "cardboardbox03_v02O",
        # "cardboardbox04_v01",
        # "cardboardbox05_v01",
        # "cardboardbox06_v01",
        # "cardboardbox07_v01",
        # "cardboardbox08_v01",
    ]
    spawn_entity_types = [entity_types[i % len(entity_types)] for i in range(17)]

    spawn_slot_names = [
        "t3/Slot1",
        "I01/RackSlot1",
        "I01/RackSlot2",
        "I01/RackSlot5",
        "I01/RackSlot6",
        "H01/RackSlot1",
        "H01/RackSlot2",
        "H01/RackSlot5",
        "H01/RackSlot6",
        "t1/Slot5",
        "t1/Slot6",
        "t1/Slot7",
        "t1/Slot8",
        "t2/Slot5",
        "t2/Slot6",
        "t2/Slot7",
        "t2/Slot8",
    ]
    target_slot_names = [
        "J01/RackSlot1",
        "t3/Slot1",
        "t3/Slot2",
        "t3/Slot3",
        "t3/Slot4",
        "t4/Slot1",
        "t4/Slot2",
        "t4/Slot3",
        "t4/Slot4",
        "C04/RackSlot1",
        "C04/RackSlot2",
        "C04/RackSlot5",
        "C04/RackSlot6",
        "B04/RackSlot1",
        "B04/RackSlot2",
        "B04/RackSlot5",
        "B04/RackSlot6",
    ]

    simulation_names = scene_manager.populate_scene(
        spawn_slot_names, spawn_entity_types
    )

    for entity_name, target_slot_name in tqdm(
        zip(simulation_names, target_slot_names),
        total=min(len(simulation_names), len(target_slot_names)),
    ):
        object_pose = scene_manager.get_pose(entity_name)
        object_height = scene_manager.get_object_height(entity_name)
        slot_pose = scene_manager.get_slot_pose(target_slot_name)
        kairos_controller.move_object_to_slot(slot_pose, object_pose, object_height)

    connector.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(**vars(args))
