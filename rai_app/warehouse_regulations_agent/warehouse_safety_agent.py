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
from typing import Any, List, TypedDict

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import START, StateGraph
from pydantic import BaseModel, Field


class VisionObservation(BaseModel):
    """Intermediate vision-only description before retrieval."""

    image_description: str = Field(
        ..., description="Detailed description of the image."
    )
    anomalies: List[str] = Field(
        default_factory=list,
        description="List of hypothesized anomalies or potential hazards.",
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
    # TODO (mkotynia): change it to one Violation
    violations: List[Violation] = Field(
        default_factory=list,
        description="List of identified safety violations with details",
    )


class ImageRegAgentState(TypedDict, total=False):
    messages: List[BaseMessage]
    vision: VisionObservation | dict[str, Any]
    retrieval_context: str
    output: FinalImageSafetyOutput | dict[str, Any] | Any


VISION_SYSTEM_PROMPT = f"""You are an safety expert who is responsible for inspecting
the safety compliance of warehouse environments. Describe the image in a very detail and
tell whether do you see any anomalies or potential safety hazards. Return your response
in structured output format:{VisionObservation.model_json_schema()}. Return up to 3 most
relevant anomalies. Focus on anomalies that are regulated by OSHA and on errors that
are made by humans like wrong or hazardous placements, obstructions, other hazards, ppe
equipment. If not severe skip anomalies that are about markings or objects that are not
visible in the image. Don't force anomalies that are not obviouse from OSHA standpoint, 
it's fine to leave anomalies list empty. Boxes that lay on the floor under the racks are not considered as anomalies in this warehouse.
Describe fire extinguishers in the image. 
"""

FINAL_SYSTEM_PROMPT_TEMPLATE = (
    "Based on the image description and retrieved regulations describe why you consider the anomaly a violation of the regulations."
    "Task: For each anomaly decide if it is a violation of the regulations. "
    "For violations produce hazard, applicable regulations (number + excerpt), "
    "severity (LOW/MEDIUM/HIGH), and rationale. Be concise, factual, and base "
    "reasoning on retrieved regulations and the image description."
    "If not severe skip anomalies that are about markings or objects that are not"
    "visible in the image. Don't force anomalies that are not obviouse from OSHA standpoint, "
    "it's fine to leave anomalies list empty."
    "Boxes that lay on the floor under the racks are not considered as anomalies in this warehouse."
    "Describe fire extinguishers in the image."
)


def _vision_node(llm_vision: Any, state: ImageRegAgentState):
    ts = time.perf_counter()
    msgs = state.setdefault("messages", [])
    if msgs and not isinstance(msgs[0], SystemMessage):
        msgs.insert(0, SystemMessage(content=VISION_SYSTEM_PROMPT))
    logging.info("Running vision node...")
    result = llm_vision.invoke(msgs)
    parsed = result["parsed"]
    if parsed.anomalies and len(parsed.anomalies) > 3:
        parsed.anomalies = parsed.anomalies[:3]

    state["vision"] = parsed
    logging.info(f"Image description: {parsed.image_description}")
    # msgs.append(result["raw"])
    msgs.append(AIMessage(content=str(parsed)))
    logging.info(f"Vision node took {time.perf_counter() - ts}")
    return state


def _retrieval_node(vector_store: Any, state: ImageRegAgentState, k: int = 3):
    msgs = state.setdefault("messages", [])
    vision = state.get("vision")
    if not vision or not vision.anomalies:
        logging.info("No anomalies to process")
        return state  # No anomalies to process

    retrieved_per_anomaly = {}
    logging.info("Running retrieval node...")
    for anomaly in vision.anomalies:
        ts = time.perf_counter()
        docs = vector_store.similarity_search(anomaly, k=k)
        retrieved_per_anomaly[anomaly] = docs
        msgs.append(
            AIMessage(content=f"Retrieved regulations for anomaly '{anomaly}':\n{docs}")
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
            result = llm_final.invoke(payload)

        if result["parsed"]:
            violations.extend(
                result["parsed"]
                if isinstance(result["parsed"], list)
                else [result["parsed"]]
            )
        msgs.append(result["raw"])
        logging.info(
            f"Final node for anomaly '{anomaly}' took {time.perf_counter() - ts}"
        )
    # TODO (mkotynia): merge all messages with violations to one AIMessage
    state["output"] = violations
    return state


def create_image_regulation_agent(
    *,
    vlm: BaseChatModel,
    llm: BaseChatModel,
    vector_store,
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
    graph.add_node("retrieve", partial(_retrieval_node, vector_store, k=k))
    graph.add_node(
        "final",
        partial(_final_structured_node, final_llm, FINAL_SYSTEM_PROMPT_TEMPLATE),
    )

    graph.add_edge(START, "vision")
    graph.add_edge("vision", "retrieve")
    graph.add_edge("retrieve", "final")

    return graph.compile()
