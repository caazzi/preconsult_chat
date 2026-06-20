import logging
from langchain_google_vertexai import ChatVertexAI
from .config import LLM_MODEL, VERTEX_REGION, PROJECT_ID

_llm = None

def get_llm() -> ChatVertexAI:
    global _llm
    if _llm is None:
        logging.info("Initializing Vertex AI LLM for the first time...")
        _llm = ChatVertexAI(
            model_name=LLM_MODEL,
            temperature=0.2,
            project=PROJECT_ID,
            location=VERTEX_REGION,
            streaming=True
        )
        logging.info("Vertex AI LLM initialized successfully.")
    return _llm
