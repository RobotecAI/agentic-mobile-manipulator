import getpass
import os
import argparse
from pathlib import Path

if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

# llm = ChatOpenAI(model="gpt-4o-mini", base_url="https://api.openai.com/v1/")
llm = ChatOllama(model="qwen2.5vl:7b", base_url="http://localhost:11434")

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.language_models import BaseChatModel

from rai import get_tracing_callbacks

from warehouse_safety_agent import create_image_regulation_agent
from rai.messages import HumanMultimodalMessage, preprocess_image
from rai.initialization import get_llm_model

def load_vector_store(db_path: str) -> FAISS:
    """Load an existing FAISS vector store from the specified path."""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Vector database not found at: {db_path}")
    
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    
    vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    print(f"Loaded vector store from: {db_path}")
    return vector_store

def run_agent(vector_store: FAISS, image_path: str, llm: BaseChatModel, vlm: BaseChatModel):
    """Run the image regulation agent with the given vector store and image."""
    agent = create_image_regulation_agent(
        vlm=vlm,
        llm=llm,
        vector_store=vector_store,
        k=3,
    )
    
    state = agent.invoke({
        "messages": [
            HumanMultimodalMessage(
                content="Describe the image in a very detail and identify the potential anomalies. Put attention to the anomalies and potential safety hazards related to warehouse environment. Return your response in structured output format - include image description and list of potential anomalies if any.",
                images=[preprocess_image(image_path)],
            )
        ]
    }, config={"callbacks": get_tracing_callbacks()})
    
    output = state.get("output") if isinstance(state, dict) else state
    print(output)

def main():
    parser = argparse.ArgumentParser(
        description="Run warehouse safety regulation agent with pre-built vector database"
    )
    parser.add_argument(
        "--vision-model", "-m",
        default="qwen2.5vl:7b",
        help="VLM model to use for image analysis (default: qwen2.5vl:7b)"
    )
    parser.add_argument(
        "--final-output-model", "-f",
        required=False,
        help="LLM model to use for final assessment in case the user wants to use other model than vision model"
    )
    parser.add_argument(
        "--vector-db", "-d",
        required=True,
        help="Path to the FAISS vector database directory"
    )
    parser.add_argument(
        "--image", "-i",
        default="images/image_17.png",
        help="Path to the image to analyze (default: images/image_17.png)"
    )
    
    args = parser.parse_args()
    
    vector_store = load_vector_store(args.vector_db)

    vlm = ChatOllama(model=args.vision_model, base_url="http://localhost:11434")

    if args.final_output_model:
        llm = ChatOllama(model=args.final_output_model, base_url="http://localhost:11434")
    else:
        llm = vlm
    run_agent(vector_store=vector_store, image_path=args.image, llm=llm, vlm=vlm)

if __name__ == "__main__":
    main()