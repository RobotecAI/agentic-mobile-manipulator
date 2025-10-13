import argparse
import json
import random
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.language_models import BaseChatModel
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI
from rai.messages import HumanMultimodalMessage, preprocess_image

from rai_app.warehouse_regulations_agent.warehouse_safety_agent import (
    create_image_regulation_agent,
)


def load_vector_store(db_path: str) -> FAISS:
    """Load an existing FAISS vector store from the specified path."""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Vector database not found at: {db_path}")

    embeddings = OllamaEmbeddings(model="mxbai-embed-large")

    vector_store = FAISS.load_local(
        db_path, embeddings, allow_dangerous_deserialization=True
    )
    print(f"Loaded vector store from: {db_path}")
    return vector_store


def run_agent(
    vector_store: FAISS,
    image_path: str,
    llm: BaseChatModel,
    vlm: BaseChatModel,
    k: int = 3,
):
    """Run the image regulation agent with the given vector store and image."""
    agent = create_image_regulation_agent(
        vlm=vlm,
        llm=llm,
        vector_store=vector_store,
        k=k,
    )

    state = dict()
    try:
        state = agent.invoke(
            {
                "messages": [
                    HumanMultimodalMessage(
                        content="Describe the image in a very detail and identify the potential anomalies. Put attention to the anomalies and potential safety hazards related to warehouse environment. Return your response in structured output format - include image description and list of potential anomalies if any.",
                        images=[preprocess_image(image_path)],
                    )
                ]
            },
            # config={"callbacks": get_tracing_callbacks()},
        )
    except Exception as e:
        logging.error(f"Error running agent: {e}")
        state["output"] = "Failed to run agent"
        return state
    return state


def main():
    parser = argparse.ArgumentParser(
        description="Run warehouse safety regulation agent with pre-built vector database"
    )
    parser.add_argument(
        "--vision-model",
        required=False,
        help="VLM model to use for image analysis (default: qwen2.5vl:7b)",
    )
    parser.add_argument(
        "--base-url",
        required=False,
        default=None,
        help="Base URL for the VLM model",
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
        default=3,
        help="Number of nearest neighbors to retrieve from the vector database (default: 3)",
    )

    args = parser.parse_args()

    vector_store = load_vector_store(args.vector_db)

    vlm_model = args.vision_model
    vlm = ChatOpenAI(
        model=vlm_model,
        base_url=args.base_url,
        timeout=20,
    )

    images_dir = Path(args.images_dir)
    images = list(set(list(images_dir.rglob("*.png"))))
    random.shuffle(images)
    for image_path in images:
        output_path = f"{image_path}.{vlm_model}.violations.jsonl"
        output_path_id = f"{image_path}.{vlm_model}.image_description.jsonl"
        if Path(output_path).exists():
            logging.info(f"Skipping image: {output_path} because it already exists")
            continue
        ts = time.perf_counter()
        logging.info(f"Processing image: {image_path}")
        state = run_agent(
            vector_store=vector_store,
            image_path=str(image_path),
            llm=vlm,
            vlm=vlm,
            k=args.k,
        )
        if state is str:
            output = state
        else:
            output = state.get("output") if isinstance(state, dict) else state
        logging.info(f"Output: {output}")

        if "vision" in state:
            with open(output_path_id, "w") as f:
                json.dump(state["vision"].image_description, f)

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
