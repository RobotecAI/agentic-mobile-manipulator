import math
from typing import Optional

from geometry_msgs.msg import Point, Quaternion
from geometry_msgs.msg import Pose as PoseMsg
from pydantic import BaseModel


def yaw_to_quaternion(yaw: float) -> Quaternion:
    half_yaw = yaw / 2.0
    return Quaternion(x=0.0, y=0.0, z=math.sin(half_yaw), w=math.cos(half_yaw))


class Pose(BaseModel):
    x: float
    y: float
    z: float
    yaw: Optional[float] = None

    def to_ros2_pose(self) -> PoseMsg:
        if self.yaw is not None:
            return PoseMsg(
                position=Point(x=self.x, y=self.y, z=self.z),
                orientation=self._yaw_to_quaternion(),
            )
        else:
            return PoseMsg(
                position=Point(x=self.x, y=self.y, z=self.z),
                orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
            )

    def _yaw_to_quaternion(self) -> Quaternion:
        yaw_value = self.yaw if self.yaw is not None else 0.0
        return yaw_to_quaternion(yaw_value)
