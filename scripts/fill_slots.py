import random

from rai.communication.ros2 import ROS2Connector

from rai_app.environment import SceneManager


def main(
    connector=None,
    clear=True,
    entity_types: list[str] | None = None,
    skip_slots: list[str] | None = None,
    fraction_of_slots: int | None = None,
):
    """
    Fill slots with entities

    Args:
        connector (ROS2Connector, optional): ROS2 connector. Defaults to None.
        clear (bool, optional): Clear the scene. Defaults to True.
        entity_types (list[str] | None, optional): List with entity types. Defaults to None.
        skip_slots (list[str] | None, optional): List with slot names to skip. Exact names can be passed or substrings of names. E.g. ["H01/RackSlot1", "H02", "t2"]. Defaults to None.
        fraction_of_slots (int | None, optional): Use 1/fraction_of_slots for spawning. Defaults to None.
    """
    if connector is None:
        connector = ROS2Connector(
            executor_type="multi_threaded", node_name="ground_truth_manipulation"
        )
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    if clear:
        scene_manager.clear_scene()

    if entity_types is None:
        entity_types = [
            item
            for item in scene_manager.spawnable_to_uri
            if item.startswith("cardboardbox")
        ]

    all_slot_names = []

    empty_slots = (
        scene_manager.find_empty_slots_on_racks()
        | scene_manager.find_empty_slots_on_tables()
    )

    # Select 1/x of all slots randomly
    if fraction_of_slots:
        empty_slots = {
            rack: random.sample(slots, max(1, len(slots) // fraction_of_slots))
            for rack, slots in empty_slots.items()
        }

    for rack in empty_slots:
        for slot in empty_slots[rack]:
            all_slot_names.append(slot.tag)

    if skip_slots is not None:
        all_slot_names = [
            slot for slot in all_slot_names if all(s not in slot for s in skip_slots)
        ]

    spawn_slot_names = all_slot_names
    spawn_entity_types = [
        entity_types[i % len(entity_types)] for i in range(len(spawn_slot_names))
    ]

    scene_manager.populate_scene(
        spawn_slot_names, spawn_entity_types, std_xy=0.05, std_yaw=0.08
    )


if __name__ == "__main__":
    import argparse

    import rclpy

    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    rclpy.init()
    main(**vars(args))
