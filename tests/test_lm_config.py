from hashlib import sha256
from typing import Literal

import pytest
from rai.messages import HumanMultimodalMessage

from rai_app.llms import (
    get_embeddings_model,
    get_llm_model,
    get_vlm_model,
)


def test_embeddings_model() -> None:
    SHA256_HASH = "96ed3644f17076a4e3a83742c4b118859fbb5eade632de7af7469f522ecc968a"
    embeddings_model = get_embeddings_model("safety_agent")
    embedding = embeddings_model.embed_query("Hello, world!")
    sha256_hash = sha256(str(embedding).encode()).hexdigest()
    if sha256_hash != SHA256_HASH:
        raise ValueError(
            f"Embeddings model returned different hash than expected: {sha256_hash} != {SHA256_HASH}"
        )


@pytest.mark.parametrize("agent_name", ["megamind_agent", "general"])
def test_llm_model(agent_name: Literal["megamind_agent", "general"]) -> None:
    llm_model = get_llm_model(agent_name)
    llm_model.invoke("Hello, world!")


@pytest.mark.parametrize(
    "agent_name", ["megamind_agent", "inspection_agent", "safety_agent", "general"]
)
def test_vlm_model(
    agent_name: Literal[
        "megamind_agent", "inspection_agent", "safety_agent", "general"
    ],
    base64_image: str,
) -> None:
    vlm_model = get_vlm_model(agent_name)
    vlm_model.invoke(
        [HumanMultimodalMessage(content="Hello, world!", images=[base64_image])]
    )
