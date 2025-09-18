import csv

from rai.communication.ros2 import ROS2Connector, ROS2Context

from scripts.scene_manager import SceneManager


def load_spawn_config(spawn_config_file):
    """
    Load spawn configuration from CSV file.
    Expected CSV format with headers: slot_name, entity_type
    """
    spawn_slot_names = []
    spawn_entity_types = []

    with open(spawn_config_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            spawn_slot_names.append(row["slot_name"])
            spawn_entity_types.append(row["entity_type"])

    return spawn_slot_names, spawn_entity_types


def load_entity_types(entity_types_file):
    """
    Load entity types from CSV file and generate spawn pattern.
    Expected CSV format with header: entity_type
    """
    entity_types = []

    with open(entity_types_file, "r") as file:
        reader = csv.DictReader(file)
        entity_types = [row["entity_type"] for row in reader]

    return entity_types


@ROS2Context()
def main():
    connector = ROS2Connector(
        executor_type="multi_threaded", node_name="ground_truth_manipulation"
    )
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )
    scene_manager.clear_scene()
    spawn_slot_names, spawn_entity_types = load_spawn_config(
        "scripts/resources/spawn_config.csv"
    )

    scene_manager.populate_scene(spawn_slot_names, spawn_entity_types)


if __name__ == "__main__":
    main()
