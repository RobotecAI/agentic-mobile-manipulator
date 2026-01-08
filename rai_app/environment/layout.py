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

from enum import Enum

import numpy as np
from geometry_msgs.msg import Point, Pose, Quaternion
from tf_transformations import (
    quaternion_from_euler,
)

FE_Z = 1.2
FE_YAW = 0.8


class FireExtinguisherPositions(Enum):
    PILLAR1 = (15.0, 14.81, FE_Z, FE_YAW)
    PILLAR2 = (19.956525802612305, 14.81, FE_Z, FE_YAW)
    PILLAR3 = (25.02849578857422, 14.81, FE_Z, FE_YAW)
    TOP_WALL = (29.8940372467041, 14.81, FE_Z, FE_YAW)
    RIGHT_WALL = (0.2872406005859375, 8.886, FE_Z, FE_YAW)
    RIGHT_WALL2 = (11.83241081237793, 8.886, FE_Z, FE_YAW)
    BOTTOM_WALL = (0.20, 0.04998302459716, FE_Z, FE_YAW)
    LEFT_WALL = (11.25, 21.18, FE_Z, FE_YAW)

    def to_point(self, zero_z: bool = False, offset: Point = Point(x=0.0)):
        if zero_z:
            return Point(x=self.value[0] + offset.x, y=self.value[1] + offset.y, z=0.0)
        return Point(
            x=self.value[0] + offset.x,
            y=self.value[1] + offset.y,
            z=self.value[2] + offset.z,
        )

    def to_pose(self):
        q = quaternion_from_euler(0, 0, self.value[3])
        q = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        return Pose(position=self.to_point(), orientation=q)


class Layout:
    def get_right_end_of_left_racks(self, distance_between, n_rows=3):
        x1 = 15.6
        x2 = 20.43
        x3 = 25.43

        return [
            (x, y)
            for x in list(np.arange(14.9, x1, distance_between))
            + list(np.arange(19.6, x2, distance_between))
            + list(np.arange(24.5, x3, distance_between))
            for y in [16.8]
        ]

    def get_top_end_of_the_right_bottom_rack(self, distance_between):
        return [
            (x, y) for x in [9.95] for y in np.arange(4.6, 5.5, distance_between + 0.15)
        ]

    def get_bottom_left_rectangle_2(self, distance_between):
        return [
            (x, y)
            for x in np.arange(4.5, 8, distance_between)
            for y in np.arange(25.5, 25.8, distance_between)
        ]

    def get_blocking_fire_pillar(self, distance_between, pillar_index):
        if pillar_index == 1:
            pillar = FireExtinguisherPositions.PILLAR1.value
        elif pillar_index == 2:
            pillar = FireExtinguisherPositions.PILLAR2.value
        elif pillar_index == 3:
            pillar = FireExtinguisherPositions.PILLAR3.value
        else:
            raise ValueError(f"Invalid pillar index: {pillar_index}")
        return [(pillar[0], pillar[1] - 0.3)]

    def get_blocking_control_panel(self, distance_between):
        return [
            (0.4749181270599365, 1.7928094863891602),
            (0.9202837944030762, 2.5172815322875977),
            (0.7208139705657959, 3.1252699089050293),
            (0.37119102478027344, 3.7736659049987793),
            (0.5714492797851562, 0.7994723320007324),
            (1.591139793395996, 0.7337689399719238),
            (2.5593996047973633, 0.8457283973693848),
            (0.5194931030273438, 5.688401699066162),
        ]

    def get_oil_spill(self):
        return [
            (16.055522918701172, 11.142255783081055),
            (7.716455459594727, 8.602497100830078),
            (21.73844337463379, 20.6577091217041),
        ]

    def get_fallen_fire_extinguisher(self):
        return [(15.075809478759766, 14.729681777954102)]

    def get_fallen_barrels(self):
        return [
            (18.11327362060547, 3.2944107055664062),
            (17.13507843017578, 3.9411001205444336),
            (27.609996795654297, 17.445159912109375),
        ]

    def get_fallen_boxes(self):
        return [
            (24.106319427490234, 7.027811050415039),
            (24.038124084472656, 6.319151878356934),
            (23.769824981689453, 6.740094184875488),
            (26.2872314453125, 11.346431732177734),
            (23.971521377563477, 18.67508888244629),
            (24.17168426513672, 19.1826229095459),
            (23.860095977783203, 19.084598541259766),
            (24.174205780029297, 19.00274658203125),
            (23.864707946777344, 18.51069450378418),
        ]

    def get_trash_boxes(self):
        return [
            (24.90743637084961, 10.724227905273438),
            (24.409767150878906, 10.608280181884766),
            (23.88950538635254, 11.215719223022461),
            (24.130647659301758, 10.912820816040039),
            (24.660411834716797, 11.360240936279297),
            (24.18947982788086, 11.624117851257324),
            (24.372711181640625, 10.966054916381836),
            (21.780208587646484, 16.069000244140625),
        ]


def q_from_euler(yaw: float) -> Quaternion:
    q = quaternion_from_euler(0, 0, yaw)
    return Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])


def add_offset(pose: Pose, offset: Point, yaw: float):
    q = quaternion_from_euler(0, 0, yaw)
    return Pose(
        position=Point(
            x=pose.position.x + offset.x,
            y=pose.position.y + offset.y,
            z=pose.position.z + offset.z,
        ),
        orientation=Quaternion(x=q[0], y=q[1], z=q[2], w=q[3]),
    )


class KairosOrientations(Enum):
    FACE_RIGHT = q_from_euler(-np.pi / 2)
    FACE_RIGHT_UP = q_from_euler(-np.pi / 4)
    FACE_LEFT = q_from_euler(np.pi / 2)
    FACE_LEFT_UP = q_from_euler(np.pi / 4)
    FACE_RIGHT_DOWN = q_from_euler(-3 * np.pi / 4)
    FACE_LEFT_DOWN = q_from_euler(3 * np.pi / 4)
    FACE_DOWN = q_from_euler(np.pi)
    FACE_UP = q_from_euler(0)


class KairosPredefinedPoses(Enum):
    INITIAL = Pose(
        position=Point(x=2.44, y=2.48, z=0.0),
        orientation=KairosOrientations.FACE_LEFT.value,
    )
    FIRE_EXT_RIGHT_WALL = Pose(
        position=FireExtinguisherPositions.RIGHT_WALL.to_point(
            True, Point(x=0.5, y=-2.5)
        ),
        orientation=KairosOrientations.FACE_LEFT.value,
    )
    FIRE_EXT_RIGHT_WALL2 = Pose(
        position=FireExtinguisherPositions.RIGHT_WALL2.to_point(
            True, Point(x=-2.5, y=-2.5)
        ),
        orientation=KairosOrientations.FACE_UP.value,
    )
    BELOW_LEFT_TABLE = Pose(
        position=Point(x=13.7, y=12.56, z=0.0),
        orientation=KairosOrientations.FACE_LEFT_UP.value,
    )
    ABOVE_LEFT_TABLE = Pose(
        position=Point(x=26.87, y=12.56, z=0.0),
        orientation=KairosOrientations.FACE_LEFT_DOWN.value,
    )
    ABOVE_RIGHT_BOTTOM_RACK = Pose(
        position=Point(x=12.25, y=4.8, z=0.0),
        orientation=KairosOrientations.FACE_DOWN.value,
    )
    TOP_OF_LEFT_RECTANGLE = Pose(
        position=Point(x=13.09, y=25.4, z=0.0),
        orientation=KairosOrientations.FACE_DOWN.value,
    )
    LEFT_SIDE_OF_LEFT_RECTANGLE = Pose(
        position=Point(x=6.90, y=27.1, z=0.0),
        orientation=KairosOrientations.FACE_RIGHT_DOWN.value,
    )
    RIGHT_SIDE_OF_LEFT_RECTANGLE = Pose(
        position=Point(x=7.55, y=23.5, z=0.0),
        orientation=KairosOrientations.FACE_LEFT_DOWN.value,
    )
    RIGHT_CENTER_OF_RIGHT_TABLE_DOWN = Pose(
        position=Point(x=19.0, y=8.6, z=0.0),
        orientation=KairosOrientations.FACE_DOWN.value,
    )
    BOTTOM_OF_RIGHT_RACKS = Pose(
        position=Point(x=12.764026641845703, y=4.22290563583374, z=0.0),
        orientation=KairosOrientations.FACE_DOWN.value,
    )
    IN_FROM_OF_CONTROL_PANEL = Pose(
        position=Point(x=2.562185764312744, y=2.818967342376709, z=0.0),
        orientation=KairosOrientations.FACE_DOWN.value,
    )


class KairosTrajectories(Enum):
    """The idea is that the anomaly is visible by kairos for all the time during the trajectoru"""

    FIRE_EXT_ANOMALY_RIGHT_WALL: tuple[Pose, Pose] = (
        KairosPredefinedPoses.INITIAL.value,
        KairosPredefinedPoses.FIRE_EXT_RIGHT_WALL.value,
    )
    FIRE_EXT_ANOMALY_RIGHT_WALL2: tuple[Pose, Pose] = (
        Pose(
            position=FireExtinguisherPositions.RIGHT_WALL.to_point(
                True, Point(x=0.5, y=-2.5)
            ),
            orientation=KairosOrientations.FACE_UP.value,
        ),
        KairosPredefinedPoses.FIRE_EXT_RIGHT_WALL2.value,
    )
    BELOW_LEFT_TABLE_TO_PILLAR1: tuple[Pose, Pose] = (
        KairosPredefinedPoses.BELOW_LEFT_TABLE.value,
        Pose(
            position=FireExtinguisherPositions.PILLAR1.to_point(
                True, Point(x=-1.0, y=-1.5)
            ),
            orientation=KairosOrientations.FACE_LEFT_UP.value,
        ),
    )
    BELOW_LEFT_TABLE_TO_PILLAR2: tuple[Pose, Pose] = (
        KairosPredefinedPoses.BELOW_LEFT_TABLE.value,
        Pose(
            position=FireExtinguisherPositions.PILLAR2.to_point(
                True, Point(x=-2.0, y=-1.0)
            ),
            orientation=KairosOrientations.FACE_UP.value,
        ),
    )
    ABOVE_LEFT_TABLE_TO_PILLAR3: tuple[Pose, Pose] = (
        KairosPredefinedPoses.ABOVE_LEFT_TABLE.value,
        Pose(
            position=FireExtinguisherPositions.PILLAR3.to_point(
                True, Point(x=1.0, y=-1.5)
            ),
            orientation=KairosOrientations.FACE_LEFT_DOWN.value,
        ),
    )
    OBJECTS_TOWER_LEFT_RACKS: tuple[Pose, Pose] = (
        KairosPredefinedPoses.BELOW_LEFT_TABLE.value,
        Pose(
            position=FireExtinguisherPositions.PILLAR2.to_point(
                True, Point(x=-2.0, y=-1.0)
            ),
            orientation=KairosOrientations.FACE_LEFT_UP.value,
        ),
    )
    OBJECTS_TOWER_RIGHT_BOTTOM_RACK: tuple[Pose, Pose] = (
        KairosPredefinedPoses.RIGHT_CENTER_OF_RIGHT_TABLE_DOWN.value,
        KairosPredefinedPoses.ABOVE_RIGHT_BOTTOM_RACK.value,
    )
    OBJECTS_TOWER_LEFT_RECTANGLE_TO_LEFT: tuple[Pose, Pose] = (
        KairosPredefinedPoses.TOP_OF_LEFT_RECTANGLE.value,
        KairosPredefinedPoses.LEFT_SIDE_OF_LEFT_RECTANGLE.value,
    )
    OBJECTS_TOWER_LEFT_RECTANGLE_TO_RIGHT: tuple[Pose, Pose] = (
        KairosPredefinedPoses.TOP_OF_LEFT_RECTANGLE.value,
        KairosPredefinedPoses.RIGHT_SIDE_OF_LEFT_RECTANGLE.value,
    )
    TO_CONTROL_PANEL: tuple[Pose, Pose] = (
        KairosPredefinedPoses.BOTTOM_OF_RIGHT_RACKS.value,
        KairosPredefinedPoses.IN_FROM_OF_CONTROL_PANEL.value,
    )
    INCORRECT_LADDER_POSITION_BOTTOM: tuple[Pose, Pose] = (
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=-0.5, y=0.0, z=0.0), 0),
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=1.0, y=1.0, z=0.0), 0),
    )
    INCORRECT_LADDER_POSITION_BOTTOM_2: tuple[Pose, Pose] = (
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=-0.5, y=0.0, z=0.0), 0),
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=1.0, y=-1.0, z=0.0), 0),
    )
    INCORRECT_LADDER_POSITION_BOTTOM_3: tuple[Pose, Pose] = (
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=3.5, y=0.0, z=0.0), 0),
        add_offset(KairosPredefinedPoses.INITIAL.value, Point(x=9.0, y=0.0, z=0.0), 0),
    )
    DEMO_SAFETY_SCENARIO: list[Pose] = [
        Pose(
            position=Point(x=12.213827133178711, y=3.0466060638427734, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.9999550053563874, w=0.00948616164249874
            ),
        ),
        Pose(
            position=Point(x=4.150787353515625, y=3.0320005416870117, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=0.8715608136712126, w=0.49028741374093393
            ),
        ),
        Pose(
            position=Point(x=5.944170951843262, y=7.230934143066406, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=0.037891881185074645, w=0.99928184479668
            ),
        ),
        Pose(
            position=Point(x=12.61890983581543, y=7.468022346496582, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=0.5007024046986598, w=0.8656194902663522
            ),
        ),
        Pose(
            position=Point(x=13.765205383300781, y=11.673969268798828, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=0.679576552883931, w=0.7336045997472983
            ),
        ),
        Pose(
            position=Point(x=15.962980270385742, y=13.871747970581055, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=0.018715108826688205, w=0.9998248570132697
            ),
        ),
        Pose(
            position=Point(x=22.088581085205078, y=14.06313419342041, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.03502278006316292, w=0.9993865142559446
            ),
        ),
        Pose(
            position=Point(x=27.2923583984375, y=10.625632286071777, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.7513487044070476, w=0.6599053904809772
            ),
        ),
        Pose(
            position=Point(x=22.9776611328125, y=7.516634941101074, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.826097263972879, w=0.563527559624659
            ),
        ),
        Pose(
            position=Point(x=17.616586685180664, y=7.473576545715332, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.7924310941897594, w=0.6099614421922263
            ),
        ),
        Pose(
            position=Point(x=11.919633865356445, y=5.139680862426758, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=-0.9176999896818748, w=0.3972741231667208
            ),
        ),
    ]
