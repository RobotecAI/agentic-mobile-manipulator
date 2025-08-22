from langchain_openai import ChatOpenAI
from place import PlaceCollection
from rai.agents.langchain.core import create_react_runnable
from rai.communication.ros2 import ROS2Connector, ROS2Context
from rai.messages import HumanMessage, SystemMessage
from rai.tools.ros2 import GetROS2ImageConfiguredTool
from tools import navigate_to_place


@ROS2Context()
def main():
    places = PlaceCollection.from_json("agent/pose_dataset.json")

    llm = ChatOpenAI(model="gpt-4o-mini")

    ros2_connector = ROS2Connector()

    agent = create_react_runnable(
        tools=[
            navigate_to_place,
            GetROS2ImageConfiguredTool(
                connector=ros2_connector, topic="/rgbd_camera/camera_image_color"
            ),
        ],
        llm=llm,
    )
    [
        msg.pretty_print()
        for msg in agent.invoke(
            {
                "messages": [
                    SystemMessage(
                        "You are an agent deployed on a mobile robot. You are tasked with navigating per user request. Here are the places you can navigate to: "
                        + str(places)
                    ),
                    HumanMessage(
                        "Navigate to the place of your choice. At the place, grab an image and describe it."
                    ),
                ]
            },
            config={"configurable": {"places": places}},
        )["messages"]
    ]
    ros2_connector.shutdown()


if __name__ == "__main__":
    main()
