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

import pytest
from moveit_msgs.msg import MoveItErrorCodes


def decode_error_code(code: MoveItErrorCodes) -> str:
    code = code.val
    for name, value in MoveItErrorCodes.__dict__.items():
        if isinstance(value, int) and value == code:
            return name
    return "UNKNOWN"


@pytest.mark.parametrize(
    "code, expected",
    [
        (1, "SUCCESS"),
        (-31, "NO_IK_SOLUTION"),
    ],
)
def test_error_code_decode(code, expected):
    assert decode_error_code(code) == expected
