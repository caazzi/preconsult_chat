"""Provider-neutrality is an executable property, not a convention.

These tests fail when a vendor SDK or vendor exception type leaks outside the
one module allowed to know about providers, or when a third adapter cannot be
added without touching the service layer.
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "preconsult"

# Vendor packages must be imported only inside the provider seam. Match import
# statements, not prose: "boto3 credential chain" in a comment is not a leak.
VENDOR_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+"
    r"(botocore|boto3|langchain_aws|langchain_google_genai|google\.genai|google\.api_core)\b",
    re.MULTILINE,
)

ALLOWED = {SRC / "core" / "llm.py"}


def test_vendor_sdks_are_confined_to_the_provider_seam():
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        if path in ALLOWED:
            continue
        text = path.read_text(encoding="utf-8")
        for match in VENDOR_IMPORT.finditer(text):
            offenders.append(f"{path.relative_to(SRC)}: {match.group(1)}")

    assert offenders == [], (
        "vendor SDK imports leaked outside core/llm.py: " + ", ".join(offenders)
    )


def test_the_api_layer_does_not_register_vendor_exception_handlers():
    app_source = (SRC / "api" / "app.py").read_text(encoding="utf-8")

    assert VENDOR_IMPORT.search(app_source) is None, (
        "api/app.py must register provider-neutral handlers only"
    )


def test_adding_a_provider_needs_only_the_seam_module():
    """A third adapter registers in the seam and works without other edits."""
    from langchain_core.messages import AIMessageChunk

    import preconsult.core.llm as llm_module

    class ThirdProvider:
        provider = "third"

        def __init__(self, config: llm_module.LLMConfig) -> None:
            self.config = config
            self.model = config.model

        async def astream(self, messages, tools=None):
            async for delta in llm_module.deltas_from_chunks(
                [AIMessageChunk(content="1. A?\n2. B?")]
            ):
                yield delta

    config = llm_module.LLMConfig(
        provider="third",
        model="m",
        region="r",
        temperature=0.0,
        max_tokens=10,
        ttft_timeout_s=1.0,
        idle_timeout_s=1.0,
        max_retries=0,
    )

    llm_module.PROVIDERS["third"] = ThirdProvider
    try:
        client = llm_module.build_client(config)
        assert client.provider == "third"
        assert client.model == "m"
    finally:
        llm_module.PROVIDERS.pop("third", None)
