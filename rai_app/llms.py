from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama


def get_model(model: str, vendor: str, base_url: str, reasoning: bool = False) -> ChatOllama | ChatOpenAI:
    if vendor == "openai":
        return ChatOpenAI(model=model, base_url=base_url)
    elif vendor == "ollama":
        return ChatOllama(model=model, base_url=base_url, reasoning=reasoning)
    else:
        raise ValueError(f"Invalid vendor: {vendor}")