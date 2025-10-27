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

import json
import math
from typing import Literal

import numpy as np
import pytest
import requests
from rai.messages import HumanMultimodalMessage

from rai_app.initialization.llms import (
    get_embeddings_model,
    get_llm_model,
    get_reranker_model_url,
    get_vlm_model,
)


def test_embeddings_model() -> None:
    # WARN: llama.cpp may return a marginally different embedding on the initial request
    # Thus, L2 distance is computed between the embeddings with a specified tolerance
    L2_TOL = 5e-2  # L2 difference tolerance
    embeddings_model = get_embeddings_model("safety_agent")
    embedding = np.array(embeddings_model.embed_query("Hello, world!"))

    with open("tests/expected_embedding_qwen3_0.6b.json", "r") as f:
        expected_embedding = np.array(json.load(f)["embedding"])

    if np.linalg.norm(embedding - expected_embedding) > L2_TOL:
        raise ValueError(
            "The embedding model returned a different embedding than expected!"
        )


def test_reranker_model() -> None:
    MODEL = "Qwen3-Reranker:0.6b"
    QUERY = (
        "Retrive documents relevant to the described situation: "
        "A woman is wearing a helmet at a construction site"
    )
    DOCUMENTS = [
        "Construction site safety regulations",
        "A man is wearing a helmet",
        "A woman is watering tree saplings",
    ]
    DOCUMENTS_RELEVANCY = [
        0.46526646614074707,
        0.042255107313394547,
        0.0014686192153021693,
    ]
    REL_TOL = 5e-2
    reranker_request_json = {"model": MODEL, "query": QUERY, "documents": DOCUMENTS}
    reranker_model_url = get_reranker_model_url("safety_agent")
    reranker_response = requests.post(reranker_model_url, json=reranker_request_json)
    results = reranker_response.json()["results"]
    for idx, result in enumerate(results):
        if not math.isclose(
            result["relevance_score"], DOCUMENTS_RELEVANCY[idx], rel_tol=REL_TOL
        ):
            raise ValueError(
                (
                    "Reranker model returned a different relevancy score than expected:, "
                    f"{result['relevance_score']} != {DOCUMENTS_RELEVANCY[idx]}"
                )
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
        "megamind_agent",
        "inspection_agent",
        "safety_agent",
        "general",
        "condition_agent",
    ],
    base64_image: str,
) -> None:
    vlm_model = get_vlm_model(agent_name)
    vlm_model.invoke(
        [HumanMultimodalMessage(content="Hello, world!", images=[base64_image])]
    )
