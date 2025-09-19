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
