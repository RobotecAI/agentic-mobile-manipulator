from functools import partial
from typing import List, TypedDict, Any

from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.runnables import Runnable
from langgraph.graph import START, StateGraph


class VisionObservation(BaseModel):
    """Intermediate vision-only description before retrieval."""
    image_description: str = Field(..., description="Detailed description of the image.")
    anomalies: List[str] = Field(default_factory=list, description="List of hypothesized anomalies or potential hazards.")

class RegulationCitation(BaseModel):
    regulation_number: str = Field(..., description="Regulation identifier / number")
    excerpt: str = Field(..., description="Concise relevant excerpt from the regulation text supporting applicability")

class Violation(BaseModel):
    hazard: str = Field(..., description="The specific hazard / anomaly")
    applicable_regulations: List[RegulationCitation] = Field(..., description="Regulations that apply to this violation")
    severity: str = Field(..., description="Qualitative severity: LOW / MEDIUM / HIGH")
    rationale: str = Field(..., description="Why this is a violation referencing regulations")

class FinalImageSafetyOutput(BaseModel):
    # TODO (mkotynia): change it to one Violation
    violations: List[Violation] = Field(default_factory=list, description="List of identified safety violations with details")

class ImageRegAgentState(TypedDict, total=False):
    messages: List[BaseMessage]
    vision: VisionObservation | dict[str, Any]
    retrieval_context: str
    output: FinalImageSafetyOutput | dict[str, Any] | Any

VISION_SYSTEM_PROMPT = (
    f"""You are an safety expert who is responsible for inspecting the safety compliance of warehouse environments. Describe the image in a very detail and tell whether do you see any anomalies or potential safety hazards. Return your response in structured output format:{VisionObservation.model_json_schema()} .""")

FINAL_SYSTEM_PROMPT_TEMPLATE = (
    f"You are a warehouse safety compliance expert that is responsible for inspecting the safety compliance of warehouse environments. You should: \n"
    f"1) Provide a detailed image description and list of potential anomalies. Put attention to the anomalies and potential safety hazards related to warehouse environment. The output should be in structured output format: {VisionObservation.model_json_schema()}.\n"
    "2) Include retrieved regulation excerpts.\n"
    "Task: For each anomaly decide if it is a violation of the regulations. "
    "For violations produce hazard, applicable regulations (number + excerpt), severity (LOW/MEDIUM/HIGH), and rationale. "
    "Be concise, factual, and base reasoning on retrieved regulations and the image description."
)

def _vision_node(llm_vision: Any, state: ImageRegAgentState):
    msgs = state.setdefault("messages", [])
    if msgs and not isinstance(msgs[0], SystemMessage):
        msgs.insert(0, SystemMessage(content=VISION_SYSTEM_PROMPT))
    result = llm_vision.invoke(msgs)
    msgs.append(result["raw"])
    state["vision"] = result["parsed"]
    return state

def _retrieval_node(vector_store: Any, state: ImageRegAgentState, k: int = 3):
    msgs = state.setdefault("messages", [])
    vision = state.get("vision")
    if not vision or not vision.anomalies:
        return state  # No anomalies to process
    
    retrieved_per_anomaly = {}
    for anomaly in vision.anomalies:
        docs = vector_store.similarity_search(anomaly, k=k)
        retrieved_per_anomaly[anomaly] = docs
        msgs.append(AIMessage(content=f"Retrieved regulations for anomaly '{anomaly}':\n{docs}"))
    
    state["retrieval_context"] = retrieved_per_anomaly
    return state

def _final_structured_node(llm_final: Any, final_prompt: str, state: ImageRegAgentState):
    msgs = state.setdefault("messages", [])
    vision = state.get("vision")
    retrieval_context = state.get("retrieval_context", {})
    
    if not vision or not vision.anomalies:
        return state
    
    violations = []
    for anomaly in vision.anomalies:
        # Create a per-anomaly prompt or context
        anomaly_context = f"ANOMALY: {anomaly}\nRETRIEVED REGULATIONS:\n{retrieval_context.get(anomaly, [])}"
        per_anomaly_prompt = f"{final_prompt}\nFocus on this anomaly: {anomaly_context}"
        
        msgs[0] = SystemMessage(content=per_anomaly_prompt)
        result = llm_final.invoke(msgs)

        if result["parsed"]:
            violations.extend(result["parsed"] if isinstance(result["parsed"], list) else [result["parsed"]])
        msgs.append(result["raw"])
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


    vision_model = vlm.with_structured_output(schema=VisionObservation, include_raw=True)

    final_llm = llm.with_structured_output(schema=FinalImageSafetyOutput, include_raw=True)

    graph = StateGraph(ImageRegAgentState)
    graph.add_node("vision", partial(_vision_node, vision_model))
    graph.add_node("retrieve", partial(_retrieval_node, vector_store, k=k))
    graph.add_node("final", partial(_final_structured_node, final_llm, FINAL_SYSTEM_PROMPT_TEMPLATE))

    graph.add_edge(START, "vision")
    graph.add_edge("vision", "retrieve")
    graph.add_edge("retrieve", "final")

    return graph.compile()
