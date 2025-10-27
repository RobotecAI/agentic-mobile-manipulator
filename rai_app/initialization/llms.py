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

import os
from dataclasses import dataclass
from typing import Literal

import tomli
from langchain_openai import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings


@dataclass
class VLMConfig:
    model: str
    base_url: str
    reasoning: bool = False
    temperature: float = 0.0


@dataclass
class LLMConfig:
    model: str
    base_url: str
    reasoning: bool = False


@dataclass
class EmbeddingsConfig:
    model: str
    base_url: str


@dataclass
class RerankerConfig:
    base_url: str


@dataclass
class GeneralConfig:
    llm: LLMConfig
    vlm: VLMConfig


@dataclass
class MegamindConfig:
    llm: LLMConfig
    vlm: VLMConfig


@dataclass
class InspectionAgentConfig:
    vlm: VLMConfig


@dataclass
class SafetyAgentConfig:
    vlm: VLMConfig
    embeddings: EmbeddingsConfig
    reranker: RerankerConfig


@dataclass
class ConditionAgentConfig:
    vlm: VLMConfig


@dataclass
class Config:
    general: GeneralConfig
    megamind_agent: MegamindConfig
    inspection_agent: InspectionAgentConfig
    safety_agent: SafetyAgentConfig
    condition_agent: ConditionAgentConfig


def load_config(config_path: str = "config.toml") -> Config:
    with open(config_path, "rb") as f:
        config = tomli.load(f)
    return Config(
        general=GeneralConfig(
            llm=LLMConfig(
                model=config["general"]["llm_model"],
                base_url=config["general"]["llm_base_url"],
                reasoning=config["general"]["llm_reasoning"],
            ),
            vlm=VLMConfig(
                model=config["general"]["vlm_model"],
                base_url=config["general"]["vlm_base_url"],
                reasoning=config["general"]["vlm_reasoning"],
            ),
        ),
        megamind_agent=MegamindConfig(
            llm=LLMConfig(
                model=config["megamind_agent"]["llm_model"],
                base_url=config["megamind_agent"]["llm_base_url"],
                reasoning=config["megamind_agent"]["llm_reasoning"],
            ),
            vlm=VLMConfig(
                model=config["megamind_agent"]["vlm_model"],
                base_url=config["megamind_agent"]["vlm_base_url"],
                reasoning=config["megamind_agent"]["vlm_reasoning"],
            ),
        ),
        inspection_agent=InspectionAgentConfig(
            vlm=VLMConfig(
                model=config["inspection_agent"]["vlm_model"],
                base_url=config["inspection_agent"]["vlm_base_url"],
                reasoning=config["inspection_agent"]["vlm_reasoning"],
                temperature=config["inspection_agent"]["vlm_temperature"],
            )
        ),
        safety_agent=SafetyAgentConfig(
            vlm=VLMConfig(
                model=config["safety_agent"]["vlm_model"],
                base_url=config["safety_agent"]["vlm_base_url"],
                reasoning=config["safety_agent"]["vlm_reasoning"],
            ),
            embeddings=EmbeddingsConfig(
                model=config["safety_agent"]["embeddings_model"],
                base_url=config["safety_agent"]["embeddings_base_url"],
            ),
            reranker=config["safety_agent"]["reranker_base_url"],
        ),
        condition_agent=ConditionAgentConfig(
            vlm=VLMConfig(
                model=config["condition_agent"]["vlm_model"],
                base_url=config["condition_agent"]["vlm_base_url"],
                reasoning=config["condition_agent"]["vlm_reasoning"],
                temperature=config["condition_agent"]["vlm_temperature"],
            )
        ),
    )


def get_llm_model(config_name: Literal["megamind_agent", "general"]) -> ChatOpenAI:
    config = load_config()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key is None:
        openai_api_key = "xxx"  # ChatOpenAPI does not initialize without an API key
    if config_name == "megamind_agent":
        return ChatOpenAI(
            model=config.megamind_agent.llm.model,
            base_url=config.megamind_agent.llm.base_url,
            api_key=openai_api_key,
        )
    elif config_name == "general":
        return ChatOpenAI(
            model=config.general.llm.model,
            base_url=config.general.llm.base_url,
            api_key=openai_api_key,
        )
    else:
        raise ValueError(f"Invalid config name: {config_name}")


def get_vlm_model(
    config_name: Literal[
        "megamind_agent",
        "inspection_agent",
        "safety_agent",
        "general",
        "condition_agent",
    ],
) -> ChatOpenAI:
    config = load_config()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    print(
        config_name,
    )
    if openai_api_key is None:
        openai_api_key = "xxx"  # ChatOpenAPI does not initialize without an API key
    if config_name == "megamind_agent":
        return ChatOpenAI(
            model=config.megamind_agent.vlm.model,
            base_url=config.megamind_agent.vlm.base_url,
            api_key=openai_api_key,
        )
    elif config_name == "inspection_agent":
        return ChatOpenAI(
            model=config.inspection_agent.vlm.model,
            base_url=config.inspection_agent.vlm.base_url,
            api_key=openai_api_key,
            temperature=config.inspection_agent.vlm.temperature,
        )
    elif config_name == "safety_agent":
        return ChatOpenAI(
            model=config.safety_agent.vlm.model,
            base_url=config.safety_agent.vlm.base_url,
            api_key=openai_api_key,
        )
    elif config_name == "general":
        return ChatOpenAI(
            model=config.general.vlm.model,
            base_url=config.general.vlm.base_url,
            api_key=openai_api_key,
        )
    elif config_name == "condition_agent":
        return ChatOpenAI(
            model=config.condition_agent.vlm.model,
            base_url=config.condition_agent.vlm.base_url,
            api_key=openai_api_key,
        )
    else:
        raise ValueError(f"Invalid config name: {config_name}")


def get_embeddings_model(config_name: Literal["safety_agent"]) -> OpenAIEmbeddings:
    config = load_config()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key is None:
        openai_api_key = "xxx"  # ChatOpenAPI does not initialize without an API key
    if config_name == "safety_agent":
        return OpenAIEmbeddings(
            model=config.safety_agent.embeddings.model,
            base_url=config.safety_agent.embeddings.base_url,
        )
    else:
        raise ValueError(f"Invalid config name: {config_name}")


# Currently, there is no wrapper for the reranker. It is used directly by sending HTTP POST requests
def get_reranker_model_url(config_name: Literal["safety_agent"]):
    config = load_config()
    if config_name == "safety_agent":
        return config.safety_agent.reranker.base_url
    else:
        raise ValueError(f"Invalid agent name: {config_name}")
