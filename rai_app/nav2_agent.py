import time
from math import pi
from typing import Any, List, Optional, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from nav2_msgs.action import DriveOnHeading as Nav2DriveOnHeading
from nav2_msgs.action import FollowWaypoints as Nav2FollowWaypoints
from nav2_msgs.action import NavigateToPose as Nav2NavigateToPose
from nav2_msgs.action import Spin as Nav2Spin
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rai.agents import wait_for_shutdown
from rai.agents.base import BaseAgent
from rai.communication.ros2 import (
    ROS2Connector,
    ROS2Context,
)
from rai_interfaces.action import DriveOnHeading, FollowWaypoints, NavigateToPose, Spin
from rclpy.action.server import ServerGoalHandle
from tf_transformations import euler_from_quaternion

from rai_app.llms import get_llm_model


def decode_error_code(
    code: int,
    action_class: Nav2NavigateToPose
    | Nav2DriveOnHeading
    | Nav2Spin
    | Nav2FollowWaypoints,
) -> str:
    for name, value in action_class.Result.__dict__.items():
        if isinstance(value, int) and value == code:
            return name
    return "UNKNOWN"


def logging_wrapper(func):
    def wrapper(self, *args, **kwargs):
        RED = "\033[91m"
        GREEN = "\033[92m"
        RESET = "\033[0m"
        self.connector.node.get_logger().info(
            f"{GREEN}Calling {func.__name__} with args: {args[0].request} and kwargs: {kwargs}{RESET}"
        )
        result = func(self, *args, **kwargs)
        color = GREEN if result.success else RED
        msg = f"{color}Result of {func.__name__}: success={result.success}{RESET}"
        msg += f" {result.report}" if not result.success else ""
        self.connector.node.get_logger().info(msg)
        return result

    return wrapper


class Nav2Agent(BaseAgent):
    SYSTEM_PROMPT: str = """
    You are an agent responsible for navigating the robot to a specified position.
    You work alongside other agents and specialists to accomplish the task.
    You work within the Nav2, ROS 2 framework.
    When asked to debug, check the logs and provide short and actionable summary for the other agents.
    Make sure to mention all the important details.
    Do not propose further investigation.
    The distance is in meters. The time allowance is in seconds. The angle is in radians.
    """

    def __init__(self, llm: BaseChatModel, robot_frame: str):
        super().__init__()
        self.navigator = BasicNavigator()
        self.connector = ROS2Connector()
        self.llm = llm
        self.robot_frame = robot_frame

        self.connector.create_action(
            action_name="/rai/nav2/navigate_to_pose",
            action_type="rai_interfaces/action/NavigateToPose",
            generate_feedback_callback=self.navigate_to_pose,
        )
        self.connector.create_action(
            action_name="/rai/nav2/drive_on_heading",
            action_type="rai_interfaces/action/DriveOnHeading",
            generate_feedback_callback=self.drive_on_heading,
        )
        self.connector.create_action(
            action_name="/rai/nav2/spin",
            action_type="rai_interfaces/action/Spin",
            generate_feedback_callback=self.spin,
        )
        self.connector.create_action(
            action_name="/rai/nav2/follow_waypoints",
            action_type="rai_interfaces/action/FollowWaypoints",
            generate_feedback_callback=self.follow_waypoints,
        )
        self.logger.info("Nav2Agent initialized")

    def formulate_prompt(
        self, prompt: str, logs: str, request_params: Optional[dict[str, Any]] = None
    ) -> List[BaseMessage]:
        full_prompt = [SystemMessage(content=self.SYSTEM_PROMPT)]
        full_prompt.append(HumanMessage(content=prompt))
        full_prompt.append(HumanMessage(content=logs))
        full_prompt.append(
            HumanMessage(content=f"Request params:\n{request_params} /no_think")
        )

        return full_prompt

    def run(self):
        pass

    def stop(self):
        self.navigator.cancelTask()
        self.connector.shutdown()

    @logging_wrapper
    def navigate_to_pose(self, goal_handle: ServerGoalHandle) -> str:
        request = cast(NavigateToPose.Goal, goal_handle.request)
        self.navigator.goToPose(request.pose, request.behavior_tree)
        feedback = None
        while not self.navigator.isTaskComplete():
            time.sleep(0.1)

        result = self.navigator.getResult()
        feedback = self.navigator.getFeedback()

        action_result = NavigateToPose.Result()

        if result == TaskResult.SUCCEEDED:
            action_result.success = True
            action_result.report = "Navigated to pose successfully."
            return action_result
        elif result == TaskResult.CANCELED:
            action_result.success = False
            action_result.report = "Navigate to pose has been canceled."
            return action_result
        elif result == TaskResult.FAILED:
            reason = self.navigator.result_future.result().result.error_code
            enum_name = decode_error_code(reason, Nav2NavigateToPose)
            response = self.llm.invoke(
                self.formulate_prompt(
                    f"Navigate to pose has failed with error code {enum_name}. Check the logs and provide a short summary.",
                    str(feedback),
                    request.pose,
                )
            )
            action_result.success = False
            action_result.report = response.content
            return action_result
        else:
            action_result.success = False
            action_result.report = "Navigate to pose has unknown result. Try again."
            return action_result

    @logging_wrapper
    def drive_on_heading(self, goal_handle: ServerGoalHandle):
        request = cast(DriveOnHeading.Goal, goal_handle.request)
        params: dict[str, int | float] = {
            "dist": request.distance,
            "speed": request.speed if request.speed else 1.0,
            "time_allowance": int(
                request.time_allowance.sec + request.time_allowance.nanosec / 10**9
            )
            if request.time_allowance.sec + request.time_allowance.nanosec > 0
            else 10,
        }
        if params["dist"] == 0:
            action_result = DriveOnHeading.Result()
            action_result.success = True
            action_result.report = "The requested distance is 0. No action is required."
            return action_result

        self.navigator.driveOnHeading(**params)
        feedback = None
        while not self.navigator.isTaskComplete():
            time.sleep(0.1)
        result = self.navigator.getResult()
        feedback = self.navigator.getFeedback()

        action_result = DriveOnHeading.Result()
        if result == TaskResult.SUCCEEDED:
            goal_handle.succeed()
            action_result.success = True
            action_result.report = "Drove on heading successfully."
            return action_result
        elif result == TaskResult.CANCELED:
            goal_handle.canceled()
            action_result.success = False
            action_result.report = "Drive on heading has been canceled."
            return action_result
        elif result == TaskResult.FAILED:
            goal_handle.abort()
            reason = self.navigator.result_future.result().result.error_code
            enum_name = decode_error_code(reason, Nav2DriveOnHeading)
            response = self.llm.invoke(
                self.formulate_prompt(
                    f"Drive on heading has failed with error code {enum_name}. Check the logs and provide a short summary.",
                    str(feedback),
                    params,
                )
            )
            action_result.success = False
            action_result.report = response.content
            return action_result
        else:
            action_result.success = False
            action_result.report = "Drive on heading has unknown result. Try again."
            return action_result

    @logging_wrapper
    def spin(self, goal_handle: ServerGoalHandle):
        request = cast(Spin.Goal, goal_handle.request)

        robot_transform = self.connector.get_transform(self.robot_frame, "map")
        robot_quat = robot_transform.transform.rotation
        robot_yaw = euler_from_quaternion(
            [robot_quat.x, robot_quat.y, robot_quat.z, robot_quat.w]
        )[2]

        # clip the angle to [-pi, pi]
        request.target_yaw = (request.target_yaw + pi) % (2 * pi) - pi

        params: dict[str, int | float] = {
            "spin_dist": robot_yaw - request.target_yaw,
            "time_allowance": int(
                request.time_allowance.sec + request.time_allowance.nanosec / 10**9
            )
            if request.time_allowance.sec + request.time_allowance.nanosec > 0
            else 10,
        }

        self.navigator.spin(**params)
        while not self.navigator.isTaskComplete():
            time.sleep(0.1)

        result = self.navigator.getResult()
        feedback = self.navigator.getFeedback()

        action_result = Spin.Result()
        if result == TaskResult.SUCCEEDED:
            goal_handle.succeed()
            action_result.success = True
            action_result.report = "Turned successfully."
            return action_result
        elif result == TaskResult.CANCELED:
            goal_handle.canceled()
            action_result.success = False
            action_result.report = "Turn has been canceled."
            return action_result
        elif result == TaskResult.FAILED:
            reason = self.navigator.result_future.result().result.error_code
            enum_name = decode_error_code(reason, Nav2Spin)

            goal_handle.abort()
            response = self.llm.invoke(
                self.formulate_prompt(
                    f"Turn (requested angle: {request.target_yaw} radians) has failed with error code {enum_name}. Check the logs and provide a short summary.",
                    str(feedback),
                    params,
                )
            )
            action_result.success = False
            action_result.report = response.content
            return action_result
        else:
            action_result.success = False
            action_result.report = "Turn has unknown result. Try again."
            return action_result

    @logging_wrapper
    def follow_waypoints(self, goal_handle: ServerGoalHandle):
        request = cast(FollowWaypoints.Goal, goal_handle.request)

        for _ in range(request.number_of_loops):
            self.navigator.followWaypoints(poses=request.poses[request.goal_index :])

        while not self.navigator.isTaskComplete():
            time.sleep(0.1)

        result = self.navigator.getResult()
        feedback = self.navigator.getFeedback()

        action_result = FollowWaypoints.Result()
        if result == TaskResult.SUCCEEDED:
            goal_handle.succeed()
            action_result.success = True
            action_result.report = "Followed waypoints successfully."
            return action_result
        elif result == TaskResult.CANCELED:
            goal_handle.canceled()
            action_result.success = False
            action_result.report = "Followed waypoints has been canceled."
            return action_result
        elif result == TaskResult.FAILED:
            reason = self.navigator.result_future.result().result.error_code
            enum_name = decode_error_code(reason, Nav2Spin)

            goal_handle.abort()
            response = self.llm.invoke(
                self.formulate_prompt(
                    f"Followed waypoints has failed with error code {enum_name}. Check the logs and provide a short summary.",
                    str(feedback),
                    request.poses,
                )
            )
            action_result.success = False
            action_result.report = response.content
            return action_result
        else:
            action_result.success = False
            action_result.report = "Followed waypoints has unknown result. Try again."
            return action_result


@ROS2Context()
def main():
    llm = get_llm_model(config_name="general")
    agent = Nav2Agent(llm=llm, robot_frame="egobase_link")
    agent.run()

    wait_for_shutdown([agent])


if __name__ == "__main__":
    main()
