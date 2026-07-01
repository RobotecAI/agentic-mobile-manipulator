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

import argparse
import json
import random
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings
from rai.messages import HumanMultimodalMessage, preprocess_image

from rai_app.initialization.llms import (
    get_embeddings_model,
    get_reranker_model_url,
    get_vlm_backend,
    get_vlm_model,
)
from rai_app.warehouse_regulations_agent.warehouse_safety_agent import (
    create_image_regulation_agent,
)


def load_vector_store(
    embedding_model: OpenAIEmbeddings,
    db_path: str,
) -> FAISS:
    """Load a persisted FAISS vector store for regulation retrieval.

    Parameters
    ----------
    db_path : str
        Path to the directory containing the serialized FAISS index.

    Returns
    -------
    FAISS
        Vector store instance ready for similarity search.

    Raises
    ------
    FileNotFoundError
        If ``db_path`` does not exist.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Vector database not found at: {db_path}")

    vector_store = FAISS.load_local(
        db_path, embedding_model, allow_dangerous_deserialization=True
    )
    print(f"Loaded vector store from: {db_path}")
    return vector_store


def run_agent(
    vector_store: FAISS,
    image_path: str,
    llm: BaseChatModel,
    vlm: BaseChatModel,
    reranker_url: str,
    k: int = 3,
):
    """Generate a warehouse regulation assessment for an image.

    Parameters
    ----------
    vector_store : FAISS
        Vector store used for retrieving relevant regulations.
    image_path : str
        Path to the image subject to inspection.
    llm : BaseChatModel
        Language model handling regulatory reasoning.
    vlm : BaseChatModel
        Vision-language model providing image understanding.
    k : int, optional
        Number of nearest neighbors to retrieve from ``vector_store``.

    Returns
    -------
    dict[str, Any]
        Agent state containing vision description and potential violations.
    """
    agent = create_image_regulation_agent(
        vlm=vlm,
        llm=llm,
        vector_store=vector_store,
        reranker_url=reranker_url,
        k=k,
        vlm_backend=get_vlm_backend("safety_agent"),
        llm_backend=get_vlm_backend("safety_agent"),
    )

    state = dict()
    try:
        state = agent.invoke(
            {
                "messages": [
                    HumanMultimodalMessage(
                        content="",
                        images=[preprocess_image(image_path)],
                    )
                ]
            },
            # config={"callbacks": get_tracing_callbacks()},
        )
    except Exception as e:
        logging.error(f"Error running agent: {e}")
        state["output"] = "Failed to run agent"
        state["agent_failed"] = True
        return state
    return state


def main():
    parser = argparse.ArgumentParser(
        description="Run warehouse safety regulation agent with pre-built vector database"
    )
    parser.add_argument(
        "--vector-db",
        "-d",
        required=True,
        help="Path to the FAISS vector database directory",
    )
    parser.add_argument(
        "--images-dir",
        required=True,
        help="Path to the directory with images to analyze (default: images)",
    )
    parser.add_argument(
        "-k",
        type=int,
        default=10,
        help="Number of nearest neighbors to retrieve from the vector database (default: 10)",
    )

    args = parser.parse_args()

    vlm = get_vlm_model("safety_agent")

    llm = vlm
    embedding_model = get_embeddings_model("safety_agent")
    reranker_model_url = get_reranker_model_url("safety_agent")

    vector_store = load_vector_store(embedding_model, args.vector_db)

    images_dir = Path(args.images_dir)
    images = list(set(list(images_dir.rglob("*.png"))))
    random.shuffle(images)
    for image_path in images:
        output_path = f"{image_path}.violations.jsonl"
        output_path_id = f"{image_path}.image_description.jsonl"
        if Path(output_path).exists():
            logging.info(f"Skipping image: {output_path} because it already exists")
            continue
        ts = time.perf_counter()
        logging.info(f"Processing image: {image_path}")
        state = run_agent(
            vector_store=vector_store,
            image_path=str(image_path),
            llm=llm,
            vlm=vlm,
            reranker_url=reranker_model_url,
            k=args.k,
        )

        if state is str:
            output = state
        else:
            output = state.get("output") if isinstance(state, dict) else state
        logging.info(f"Output: {output}")

        if isinstance(state, dict) and not state.get("agent_failed", False):
            if "vision" in state:
                with open(output_path_id, "w") as f:
                    json.dump(
                        {
                            "anomaly": state["vision"].is_anomaly_present,
                            "description": state["vision"].image_description,
                        },
                        f,
                    )

            if output and isinstance(output, list):
                with open(output_path, "w") as f:
                    for violation in output:
                        if isinstance(violation, dict):
                            json.dump(violation, f)
                        else:
                            json.dump(violation.model_dump(), f)
                            f.write("\n")
                logging.info(f"Saved violations to: {output_path}")
            else:
                with open(output_path, "w") as f:
                    output = {"output": "No anomalies found"}
                    json.dump(output, f)
                logging.info(f"Saved violations to: {output_path}")

        elapsed = time.perf_counter() - ts
        logging.info(f"Time taken: {elapsed} seconds")


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
