"""Model client seam.

One provider is active per deployment, selected by ``LLM_PROVIDER``:

* ``vertex`` (default) - Google Vertex AI / Gemini, the provider the deployed
  service is configured for.
* ``bedrock`` - Anthropic Claude on AWS Bedrock, kept for the later AWS
  migration behind the same singleton seam. Needs the ``bedrock`` extra
  (``uv sync --locked --extra bedrock``); the default image ships Vertex only.

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
        # core 1.x has a first-class `timeout`; passing it through model_kwargs
        # now warns.
        timeout=30.0,
    )


def _build_bedrock():
    try:
        from langchain_aws import ChatBedrockConverse
    except ImportError as exc:
        # Bedrock is an opt-in extra so the default image does not carry
        # boto3/botocore (~34 MB) for a provider it has no credentials for.
        # Surface a config error, not an opaque 500 on the first question.
        raise RuntimeError(
            "LLM_PROVIDER=bedrock requires the 'bedrock' extra, which the "
            "default image does not install. Rebuild with "
            "`uv sync --locked --extra bedrock` (see AGENTS.md)."
        ) from exc

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
