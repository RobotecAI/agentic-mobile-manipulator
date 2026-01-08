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

import logging
import time
from functools import partial
from typing import Any, Dict, List, Optional, TypedDict

import openai
import rclpy
import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import START, StateGraph
from pydantic import BaseModel, Field
from simulation_interfaces.msg import EntityState
from simulation_interfaces.srv import GetEntitiesStates


class VisionObservation(BaseModel):
    """Intermediate vision-only description before retrieval."""

    image_description: str = Field(
        ..., description="Detailed description of the image."
    )
    anomalies: List[str] = Field(
        default_factory=list,
        description="List of hypothesized anomalies or potential hazards.",
    )
    is_anomaly_present: bool = Field(
        False, description="Whether any anomaly was identified in the image"
    )


class RegulationCitation(BaseModel):
    regulation_number: str = Field(..., description="Regulation identifier / number")
    excerpt: str = Field(
        ...,
        description="Concise relevant excerpt from the regulation text supporting applicability",
    )


class Violation(BaseModel):
    hazard: str = Field(..., description="The specific hazard / anomaly")
    applicable_regulations: List[RegulationCitation] = Field(
        ..., description="Regulations that apply to this violation"
    )
    severity: str = Field(..., description="Qualitative severity: LOW / MEDIUM / HIGH")
    rationale: str = Field(
        ..., description="Why this is a violation referencing regulations"
    )


class FinalImageSafetyOutput(BaseModel):
    is_violation_present: bool = Field(
        False, description="Whether any violation was identified"
    )
    violation: Violation = Field(
        ...,
        description="Identified safety violation with details",
    )


class ImageRegAgentState(TypedDict, total=False):
    messages: List[BaseMessage]
    vision: VisionObservation | dict[str, Any]
    retrieval_context: str
    output: FinalImageSafetyOutput | dict[str, Any] | Any


VISION_SYSTEM_PROMPT = f"""You are an Artificial Warehouse Safety Inspection Agent.
Your purpose is to analyze visual input from a warehouse environment in the context
of safety compliance and to provide a highly detailed description of what you see.
Your description will be given to a deticated safety assessor. You rely exclusively
on visual information. Do not assume, infer, or guess details that are not clearly 
visible. You must describe what you explicitly see, not what you think might be
happening. If something is ambiguous, state this clearly (e.g., “Object’s contents
unknown” rather than guessing). Your description should include relative positions of
objects and identify potential obstructions. When identifying an anomaly or hazard,
describe what is visible and why it represents a safety concern based on concrete evidence
in the image. Return your response in structured output format:{VisionObservation.model_json_schema()}. 
Return up to 3 most relevant anomalies. Focus on anomalies that are regulated by OSHA and
on errors that are made by humans like wrong or hazardous placements, obstructions, other
hazards, ppe equipment. Important notes:
- if you cannot confirm something with upmost certainty, you should not flag it as an anomaly (!),
- boxes can be laying under the racks,
- the width of the asiles is up to the required specifications,
- the safety assessor should not receive information of little relevance,
- boxes on shelves must be easily accessible for robotic arms, thus it is permitted to place boxes
on shelves without securing mechanisms
- the list of anomalies can and should be empty if no obvious violations can be seen,
- the visual input is captured by a camera at a low height and objects may appear much taller that
they actually are,
- when detecting anomalies, be aware of your inherit limitations
"""

FINAL_SYSTEM_PROMPT_TEMPLATE = """Based on the included image, image description and retrieved
regulation excerpts, decide whether the given anomaly is a violation of OSHA and a safety hazard.
If an anomaly produces a hazard, specify applicable regulations (number + excerpt), 
severity (LOW/MEDIUM/HIGH), and rationale. Be concise, factual, and base your reasoning on retrieved
regulations, the image description, and the image itself. If not severe, skip anomalies that are about
markings or objects that are not visible in the image. 
Important notes:
- if there are no clear and severe violations, set the is_violation_present flag to False,
- do not make assumptions, all violations must be supported by strong evidence,
- boxes laying on the floor under racks or shelves must not be report as a violation
Please don't report instances where manipulator obstructed the camera view.
"""

RERANKER_REQUEST_TEMPLATE = {
    "model": "Qwen3-Reranker",
    "query": "Determine which regulations are relevant to the described violation. Violation: ",
    "documents": [],
}


def get_entities(name_filter: str) -> Optional[Dict[str, EntityState]]:
    node = rclpy.create_node("get_entities_states_client")

    client = node.create_client(GetEntitiesStates, "/get_entities_states")
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error("Service /get_entities_states not available")
        return

    request = GetEntitiesStates.Request()
    request.filters.filter = name_filter

    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future)

    response = future.result()
    entities: Dict[str, EntityState] = {}
    if response is not None:
        for i, name in enumerate(response.entities):
            entities[name] = response.states[i]
        return entities
    else:
        node.get_logger().error(f"Service call failed: {future.exception()}")


def _vision_node(llm_vision: Any, state: ImageRegAgentState):
    ts = time.perf_counter()
    msgs = state.setdefault("messages", [])
    if msgs and not isinstance(msgs[0], SystemMessage):
        msgs.insert(0, SystemMessage(content=VISION_SYSTEM_PROMPT))
    logging.info("Running vision node...")
    try:
        result = llm_vision.invoke(msgs)
    except openai.LengthFinishReasonError:
        logging.error(
            "Error: Safety Agent VLM context size exceeded! Image will not be processed!"
        )
        return state
    except Exception as e:
        logging.error(f"{str(e)}. Image will not be processed!")
        return state
    parsed = result["parsed"]
    if parsed.anomalies and len(parsed.anomalies) > 3:
        parsed.anomalies = parsed.anomalies[:3]

    state["vision"] = parsed
    logging.info(f"Image description: {parsed.image_description}")
    # msgs.append(result["raw"])
    msgs.append(AIMessage(content=str(parsed)))
    logging.info(f"Vision node took {time.perf_counter() - ts}")
    return state


def _retrieval_node(
    vector_store: Any,
    state: ImageRegAgentState,
    reranker_url,
    reranker_score_threshold=0.40,
    k: int = 20,
):
    msgs = state.setdefault("messages", [])
    vision = state.get("vision")
    if not vision or not vision.anomalies:
        logging.info("No anomalies to process")
        return state  # No anomalies to process

    logging.info("Running retrieval node...")
    retrieved_per_anomaly = {}
    for anomaly in vision.anomalies:
        ts = time.perf_counter()
        docs = vector_store.similarity_search(
            f"Retrieve documents relevant to the described anomaly: {anomaly}", k=k
        )
        # Determine the relevancy of retrieved documents via a reranker
        filtered_docs_with_score = []
        # Compute the relevancy score of one doc at a time to minimize reranker memory usage
        for doc in docs:
            reranker_request = RERANKER_REQUEST_TEMPLATE.copy()
            reranker_request["query"] += anomaly
            reranker_request["documents"] = [doc.page_content]
            try:
                reranker_response = requests.post(reranker_url, json=reranker_request)
                if not reranker_response.ok:
                    logging.error(
                        f"Error: Reranker HTTP error {reranker_response.status_code}, {reranker_response.reason}. Skipping reranking!"
                    )
                else:
                    doc_score = reranker_response.json()["results"][0][
                        "relevance_score"
                    ]
                    if doc_score >= reranker_score_threshold:
                        filtered_docs_with_score.append((doc, doc_score))

            except requests.exceptions.ConnectionError:
                logging.error(
                    "Error: Could not establish connection with the RAG reranker. Skipping reranking!"
                )
                filtered_docs_with_score.append((doc, -1))
            except Exception as e:
                logging.error(f"{str(e)}. Skipping reranking!")
                filtered_docs_with_score.append((doc, -1))

        # Order docs by score
        filtered_docs_with_score.sort(key=lambda x: x[1], reverse=True)
        # Keep up to 3 docs with the highest score
        filtered_docs = [doc for doc, _ in filtered_docs_with_score[:3]]
        retrieved_per_anomaly[anomaly] = filtered_docs
        msgs.append(
            AIMessage(
                content=f"Retrieved regulations for anomaly '{anomaly}':\n{filtered_docs}"
            )
        )
        logging.info(
            f"Retrieval for anomaly '{anomaly}' took {time.perf_counter() - ts}"
        )

    state["retrieval_context"] = retrieved_per_anomaly
    return state


def _final_structured_node(
    llm_final: Any, final_prompt: str, state: ImageRegAgentState
):
    msgs = state.setdefault("messages", [])
    vision = state.get("vision")
    retrieval_context = state.get("retrieval_context", {})

    if not vision or not vision.anomalies:
        return state

    violations = []
    image_message = state["messages"][1]
    logging.info(image_message)
    for anomaly in vision.anomalies:
        ts = time.perf_counter()
        # Create a per-anomaly prompt or context
        anomaly_context = f"ANOMALY: {anomaly}\nRETRIEVED REGULATIONS:\n{retrieval_context.get(anomaly, [])}"
        image_description = vision.image_description
        per_anomaly_prompt = f"{final_prompt}\nFocus on this anomaly: {anomaly_context}"
        logging.info(
            f"Processing anomaly {anomaly}\nContext length: {len(anomaly_context)}\nImage description length: {len(image_description)}\nPrompt length: {len(per_anomaly_prompt)}"
        )

        try:
            payload = [
                SystemMessage(content=FINAL_SYSTEM_PROMPT_TEMPLATE),
                image_message,
                AIMessage(content=image_description),
                HumanMessage(content=per_anomaly_prompt),
            ]
            in_tokens_len = sum(len(m.content) for m in payload)
            logging.info(f"Input tokens length: {in_tokens_len}")
            result = llm_final.invoke(payload)
        # WARN: If context length is exceeded, other exception types may be thrown (e.g. openai.BadRequestError)
        # Exceeded context size is just one potential cause of these exceptions.
        except openai.LengthFinishReasonError:
            logging.warning(f"Trimming prompt for anomaly {anomaly}")
            # Shorten the prompt by truncating image description and anomaly context
            max_desc_len = 1000  # Adjust this value as needed
            max_context_len = 1000  # Adjust this value as needed

            shortened_desc = (
                image_description[:max_desc_len] + "..."
                if len(image_description) > max_desc_len
                else image_description
            )
            shortened_context = (
                anomaly_context[:max_context_len] + "..."
                if len(anomaly_context) > max_context_len
                else anomaly_context
            )

            payload = [
                SystemMessage(content=FINAL_SYSTEM_PROMPT_TEMPLATE),
                image_message,
                AIMessage(content=shortened_desc),
                HumanMessage(content=f"Focus on this anomaly: {shortened_context}"),
            ]
            logging.info(
                f"Repeated processing of anomaly {anomaly}\nContext length: {len(anomaly_context)}\nImage description length: {len(image_description)}\nPrompt length: {len(per_anomaly_prompt)}"
            )
            try:
                result = llm_final.invoke(payload)
            except Exception as e:
                logging.error(f"{str(e)}. Anomaly will NOT be registered!")
                continue
        except Exception as e:
            logging.error(f"{str(e)}. Anomaly will NOT be registered!")
            continue

        if result["parsed"]:
            if result["parsed"].is_violation_present:
                violations.extend(
                    result["parsed"].violation
                    if isinstance(result["parsed"].violation, list)
                    else [result["parsed"].violation]
                )
        msgs.append(result["raw"])
        logging.info(
            f"Final node for anomaly '{anomaly}' took {time.perf_counter() - ts}"
        )
    # For each anomaly the LLM is invoked with FinalImageSafetyOutput output schema
    # Thus the final output of this node is of type List[FinalImageSafetyOutput]
    state["output"] = violations
    return state


def create_image_regulation_agent(
    *,
    vlm: BaseChatModel,
    llm: BaseChatModel,
    vector_store,
    reranker_url,
    k: int = 10,
) -> Runnable[ImageRegAgentState, ImageRegAgentState]:
    """Create a 3-stage agent for image safety compliance assessment.

    Stage 1: Vision-only description & hazard extraction.
    Stage 2: Regulation retrieval per hazard (vector similarity).
    Stage 3: Structured compliance assessment (FinalImageSafetyOutput).
    """
    if vector_store is None:
        raise ValueError("vector_store is required for retrieval stage")

    vision_model = vlm.with_structured_output(
        schema=VisionObservation, include_raw=True
    )

    final_llm = llm.with_structured_output(
        schema=FinalImageSafetyOutput, include_raw=True
    )

    graph = StateGraph(ImageRegAgentState)
    graph.add_node("vision", partial(_vision_node, vision_model))
    graph.add_node(
        "retrieve",
        partial(_retrieval_node, vector_store, reranker_url=reranker_url, k=k),
    )
    graph.add_node(
        "final",
        partial(_final_structured_node, final_llm, FINAL_SYSTEM_PROMPT_TEMPLATE),
    )

    graph.add_edge(START, "vision")
    graph.add_edge("vision", "retrieve")
    graph.add_edge("retrieve", "final")

    return graph.compile()
