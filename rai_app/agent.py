import argparse
from langchain_openai import ChatOpenAI
from place import PlaceCollection
from rai.agents.langchain.core import create_react_runnable
from rai.communication.ros2 import ROS2Connector, ROS2Context
from rai.messages import HumanMessage, SystemMessage
from rai.tools.ros2 import GetROS2ImageConfiguredTool
from tools import navigate_to_place


@ROS2Context()
def main():
    parser = argparse.ArgumentParser(description="Run the mobile manipulator agent.")
    parser.add_argument("--prompt", type=str, default=None, help="Custom task prompt for the agent")
    parser.add_argument("--model-name", type=str, default="gpt-5", help="Model name to use (default: gpt-5)")
    parser.add_argument("--base-url", type=str, default=None, help="OpenAI-compatible endpoint URL")
    args = parser.parse_args()

    # Load predefined places
    places = PlaceCollection.from_json("rai_app/pose_dataset.json")

    # Initialize the language model
    llm = ChatOpenAI(model=args.model_name, base_url=args.base_url)

    # Set up ROS 2 connection
    ros2_connector = ROS2Connector()

    # Create the agent with tools for navigation and image capture
    agent = create_react_runnable(
        tools=[
            navigate_to_place,
            GetROS2ImageConfiguredTool(
                connector=ros2_connector, topic="/rgbd_camera/camera_image_color"
            ),
        ],
        llm=llm,
    )

    # Prepare messages
    system_msg = SystemMessage(
        "You are an agent deployed on a mobile robot. "
        "You are tasked with navigating per user request. "
        "Here are the predefined places you can navigate to: "
        + str(places)
    )

    human_msg = HumanMessage(
        args.prompt if args.prompt else
        "Navigate to one of the predefined points of your choosing. "
        "At the place, capture an image from the camera and describe it."
    )

    # Invoke agent
    response = agent.invoke(
            {"messages": [system_msg, human_msg]},
            config={"configurable": {"places": places}},
        )

    # Print the response messages
    for msg in response["messages"]:
        msg.pretty_print()

    # Shutdown ROS2 connector
    ros2_connector.shutdown()


if __name__ == "__main__":
    main()
