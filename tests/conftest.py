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

import numpy as np
import pytest
from rai.communication.ros2 import (
    ROS2Connector,
)
from rai.messages import preprocess_image

from rai_app.control.kairos_controller import KairosController
from rai_app.environment.scene_manager import SceneManager


@pytest.fixture
def base64_image() -> str:
    np_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    return preprocess_image(np_image)


@pytest.fixture(scope="session")
def connector():
    return ROS2Connector(executor_type="single_threaded")


@pytest.fixture(scope="session")
def scene_manager(connector: ROS2Connector):
    return SceneManager(
        slots_file="scripts/resources/slots.csv",
        spawnables_file="scripts/resources/spawnables.csv",
        connector=connector,
    )


@pytest.fixture(scope="session")
def kairos_controller(connector: ROS2Connector, scene_manager: SceneManager):
    return KairosController(connector=connector, scene_manager=scene_manager)
