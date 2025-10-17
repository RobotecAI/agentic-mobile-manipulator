import numpy as np
import pytest
from rai.messages import preprocess_image


@pytest.fixture
def base64_image() -> str:
    np_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    return preprocess_image(np_image)
