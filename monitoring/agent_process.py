import sys
from langchain_core.messages import HumanMessage
from rai.agents.langchain.core import create_conversational_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
import time


@tool
def everything_tool() -> bool:
    """Tool for everything. Always call this tool"""
    return True


def create_agent(model):
    tools = [everything_tool]
    llm = ChatOllama(model=model)
    agent = create_conversational_agent(
        llm=llm,
        tools=tools,
        system_prompt="You are robotic arm. Answer the questions and make tool calls if you can",
    )
    return agent


def main():
    model = sys.argv[1]
    agent = create_agent(model)
    messages = [
        HumanMessage("Explain the concept of artificial intelligence in simple terms.")
    ]

    while True:
        try:
            # dont log the inference metrics here
            # as it would require some multiprocess communication
            # and the metrics are already collected in main.py via
            # method make_call_to_model

            # (jmatejcz) NOTE uncomment this if you want
            # to test max load as both models will be querried at the same time
            # agent.invoke({"messages": messages})
            time.sleep(1)
        except Exception:
            break


if __name__ == "__main__":
    main()
