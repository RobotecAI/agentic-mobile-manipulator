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

"""
Assumptions:
    - You already created a FAISS index directory containing: index.faiss and index.pkl (standard FAISS.save_local output)
    - You can provide the path via --vector-store-dir
    - RAI config.toml provides an LLM accessible via get_llm_model(model_type=...)

Run:
    python examples/vector_db_react_agent.py \
        --vector-store-dir ./my_faiss_index \
        --model-type complex_model \
        --embedding-model qwen3-embedding:0.6b

"""

import argparse
import os
import textwrap
from typing import Any, Dict, List, Type

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai import get_llm_model, get_tracing_callbacks
from rai.agents.langchain import create_react_runnable
from rai.messages import HumanMultimodalMessage, preprocess_image

SYSTEM_PROMPT = """You are a warehouse safety expert. Your task is to inspect potential warehouse safety violations and identify violations in the provided image. Get necessary context from the vector database using the vector_search tool before answering questions. Justify your answers with relevant passages from the database."""


class VectorSearchToolInput(BaseModel):
    """Input schema for the vector search tool."""

    query: str = Field(description="Natural language query for semantic search")
    k: int = Field(default=10, description="Number of top documents to retrieve (1-20)")


class VectorSearchTool(BaseTool):
    """Tool that performs semantic retrieval over a persisted FAISS vector store."""

    name: str = "vector_search"
    description: str = (
        "Use this tool to retrieve background context from the knowledge base. "
        "Provide a natural language query. The tool returns the top-k passages with metadata."
    )
    args_schema: Type[VectorSearchToolInput] = VectorSearchToolInput

    # Injected dependencies
    vector_store: FAISS
    max_return_chars: int = 4000  # safety truncation

    def _run(self, query: str, k: int = 10) -> str:
        # Bound k
        k = max(1, min(20, k))
        try:
            docs = self.vector_store.similarity_search(query, k=k)
        except Exception as e:  # noqa: BLE001
            return f"Vector search failed: {e}"

        if not docs:
            return "No relevant documents found."

        formatted: List[str] = []
        for i, d in enumerate(docs, 1):
            meta = getattr(d, "metadata", {}) or {}
            snippet = d.page_content.strip().replace("\n", " ")
            snippet = textwrap.shorten(snippet, width=500, placeholder=" …")
            meta_str = (
                ", ".join(f"{k}={v}" for k, v in meta.items())
                if meta
                else "(no metadata)"
            )
            formatted.append(f"[{i}] {snippet}\n    META: {meta_str}")

        result = "Retrieved passages (use them to answer):\n" + "\n".join(formatted)
        if len(result) > self.max_return_chars:
            result = result[: self.max_return_chars] + "\n... (truncated)"
        return result


def load_faiss_vector_store(path: str, embedding_model: str) -> FAISS:
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Vector store directory not found: {path}")
    required = ["index.faiss", "index.pkl"]
    missing = [f for f in required if not os.path.exists(os.path.join(path, f))]
    if missing:
        raise FileNotFoundError(
            f"Directory {path} is missing required files: {missing}. "
            "Ensure it was saved via FAISS.save_local()"
        )

    embeddings = OllamaEmbeddings(model=embedding_model)

    store = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    return store


def build_agent(vector_store_dir: str, model_type: str, embedding_model: str):
    vector_store = load_faiss_vector_store(vector_store_dir, embedding_model)

    vector_tool = VectorSearchTool(vector_store=vector_store)

    llm = get_llm_model(model_type=model_type)

    agent = create_react_runnable(
        llm=llm,
        tools=[vector_tool],
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


question = "Does this image show any potential safety violations in the warehouse? If so, please describe them and provide relevant justification based on the vector database. Provide number of regulation that applies to the violation."
TEST_CASES: List[Dict[str, str]] = [
    {"image": "images/image_8.png", "question": question},
    {"image": "images/image_9.png", "question": question},
    {"image": "images/image_10.png", "question": question},
    {"image": "images/image_11.png", "question": question},
    {"image": "images/image_12.png", "question": question},
    {"image": "images/image_13.png", "question": question},
    {"image": "images/image_14.png", "question": question},
    {"image": "images/image_15.png", "question": question},
    {"image": "images/image_16.png", "question": question},
    {"image": "images/image_17.png", "question": question},
]


def run_test_cases(agent: Any) -> None:
    print("Running predefined test cases...")
    for idx, case in enumerate(TEST_CASES, start=1):
        question: str = case.get("question", "").strip()
        image_path: str = case.get("image", "")
        if not image_path:
            print(f"[SKIP {idx}] Missing image path entry")
            continue
        if not question:
            print(f"[SKIP {idx}] Empty question for image {image_path}")
            continue
        if not os.path.exists(image_path):
            print(f"[WARN {idx}] Image not found: {image_path}")
        state: Dict[str, List[Any]] = {"messages": []}
        try:
            images_list = (
                [preprocess_image(image_path)] if os.path.exists(image_path) else []
            )
            state["messages"].append(
                HumanMultimodalMessage(
                    content=question,
                    images=images_list,
                )
            )
            response: Any = agent.invoke(
                state, config={"callbacks": get_tracing_callbacks()}
            )
        except Exception as e:
            print(f"[ERR {idx}] Agent error for image {image_path}: {e}")
            continue
        print(f"\n=== Test Case {idx} ===")
        print(f"Image: {image_path}")
        print(f"Question: {question}")
        print("--- Response ---")
        print(response)
        print("=================\n")


def parse_args():
    parser = argparse.ArgumentParser(description="RAI vector DB ReAct agent demo")
    parser.add_argument(
        "--vector-store-dir",
        required=True,
        help="Directory containing FAISS index.faiss & index.pkl",
    )
    parser.add_argument(
        "--model-type",
        default="complex_model",
        help="Model type as defined in RAI config.toml",
    )
    parser.add_argument(
        "--embedding-model",
        default="qwen3-embedding:0.6b",
        help="Ollama embedding model name used when the index was created",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    agent = build_agent(
        vector_store_dir=args.vector_store_dir,
        model_type=args.model_type,
        embedding_model=args.embedding_model,
    )
    run_test_cases(agent)


if __name__ == "__main__":
    main()
