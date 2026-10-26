"""Model client seam.

One provider is active per deployment, selected by ``LLM_PROVIDER``:

* ``vertex`` (default) - Google Vertex AI / Gemini, the provider the deployed
  service is configured for.
* ``bedrock`` - Anthropic Claude on AWS Bedrock, kept for the later AWS
  migration behind the same singleton seam.

The client class is imported lazily so the process only pays for the provider it
actually uses; callers (and tests) still only depend on ``get_llm()``.
"""

import logging

from .config import (
    BEDROCK_REGION,
    LLM_MODEL,
    LLM_PROVIDER,
    PROJECT_ID,
    VERTEX_REGION,
)

_llm = None


def _build_vertex():
    from langchain_google_vertexai import ChatVertexAI

    return ChatVertexAI(
        model_name=LLM_MODEL,
        temperature=0.2,
        project=PROJECT_ID,
        location=VERTEX_REGION,
        streaming=True,
        max_retries=3,
        model_kwargs={"timeout": 30.0},
    )


def _build_bedrock():
    from langchain_aws import ChatBedrockConverse

    return ChatBedrockConverse(
        model=LLM_MODEL,
        region_name=BEDROCK_REGION,
        temperature=0.2,
        max_tokens=1024,
        # Streaming is the default for ChatBedrockConverse; requests use the
        # InvokeModelWithResponseStream API so `astream` yields token deltas.
    )


def get_llm():
    """Return the process-wide model client for the configured provider."""
    global _llm
    if _llm is None:
        logging.info("Initializing %s LLM for the first time...", LLM_PROVIDER)
        _llm = _build_bedrock() if LLM_PROVIDER == "bedrock" else _build_vertex()
        logging.info("%s LLM initialized successfully.", LLM_PROVIDER)
    return _llm
