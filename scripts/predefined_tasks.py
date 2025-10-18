import argparse

from rai.communication.ros2 import ROS2Connector, ROS2Context

from rai_app.agents.tools import SortReturnedPackageTool
from rai_app.control.kairos_controller import KairosController
from rai_app.environment import SceneManager
from rai_app.initialization.llms import get_vlm_model


def sort_returned_packages():
    connector = ROS2Connector()
    vlm = get_vlm_model(config_name="general")
    scene_manager = SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
    )
    kairos_controller = KairosController(
        connector=connector, scene_manager=scene_manager
    )
    tool = SortReturnedPackageTool(
        kairos_controller=kairos_controller,
        scene_manager=scene_manager,
        connector=connector,
        vlm=vlm,
    )
    while True:
        result = tool._run()
        print(result)
        if result == "No more packages to sort. All packages have been sorted.":
            break
    connector.shutdown()


@ROS2Context()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default="sort", choices=["sort"])
    args = parser.parse_args()
    if args.task == "sort":
        sort_returned_packages()
    else:
        raise ValueError(f"Invalid task: {args.task}")


if __name__ == "__main__":
    main()
