import logging
from langchain_aws import ChatBedrockConverse
from .config import LLM_MODEL, BEDROCK_REGION

_llm = None


def get_llm() -> ChatBedrockConverse:
    global _llm
    if _llm is None:
        logging.info("Initializing AWS Bedrock LLM for the first time...")
        _llm = ChatBedrockConverse(
            model=LLM_MODEL,
            region_name=BEDROCK_REGION,
            temperature=0.2,
            max_tokens=1024,
            # Streaming is the default for ChatBedrockConverse; requests use the
            # InvokeModelWithResponseStream API so `astream` yields token deltas.
        )
        logging.info("Bedrock LLM initialized successfully.")
    return _llm
