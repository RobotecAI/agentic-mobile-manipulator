from typing import Optional

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_model(
    model: str, vendor: str, base_url: Optional[str] = None, reasoning: bool = False
) -> ChatOllama | ChatOpenAI:
    if vendor == "openai":
        return ChatOpenAI(model=model, base_url="http://localhost:8084")
    elif vendor == "ollama":
        return ChatOllama(
            model=model,
            base_url="http://via-ip-robo-srv-004.robotec.tm.pl:11434",
            reasoning=reasoning,
        )
    else:
        raise ValueError(f"Invalid vendor: {vendor}")
