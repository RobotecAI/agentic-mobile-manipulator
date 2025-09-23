from rai.communication.ros2 import ROS2Connector, ROS2Context
from scene_manager import SceneManager


@ROS2Context()
def main(debug: bool = False, namespace=""):
    connector = ROS2Connector(
        executor_type="multi_threaded", node_name="ground_truth_manipulation"
    )
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    scene_manager.clear_scene()

    entity_types = [
        "cardboardbox01_v01",
        "cardboardbox01_v02D",
        "cardboardbox01_v03",
        "cardboardbox02_v01",
        "cardboardbox02_v02D",
        "cardboardbox03_v01",
        "cardboardbox03_v02O",
        "cardboardbox04_v01",
        "cardboardbox05_v01",
        "cardboardbox06_v01",
        "cardboardbox07_v01",
        "cardboardbox08_v01",
    ]

    all_slot_names = []

    empty_slots = (
        scene_manager.find_empty_slots_on_racks()
        | scene_manager.find_empty_slots_on_tables()
    )
    for rack in empty_slots:
        for slot in empty_slots[rack]:
            all_slot_names.append(f"{slot}")
    spawn_slot_names = all_slot_names
    spawn_entity_types = [
        entity_types[i % len(entity_types)] for i in range(len(spawn_slot_names))
    ]

    scene_manager.populate_scene(
        spawn_slot_names, spawn_entity_types, std_xy=0.05, std_yaw=0.05
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--namespace", type=str, default="")
    args = parser.parse_args()
    main(**vars(args))
