"""Capture a real provider's raw stream chunks, for the contract fixtures.

Dev-only and never run in CI. Needs live provider credentials.

    uv run python scripts/capture_llm_stream.py --out /tmp/bedrock.json

The captured file records only chunk *shape* (content, tool calls, usage) plus
whatever text the model produced from the synthetic prompt below. Nothing is
committed: point ``--out`` at ``/tmp`` unless you have reviewed the output and
passed ``--allow-fixtures``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "llm"

# Deliberately synthetic: no patient data, and short enough that the capture is
# cheap. The point is the wire format, not the model's answer.
SYNTHETIC_INPUT: dict[str, Any] = {
    "age_bracket": "26-35",
    "sex": "Female",
    "specialist": "Cardiology",
    "chief_complaint": "Chest pain",
    "duration": "2 days",
    "complaint_detail": "None",
    "conditions": "None",
    "medications": "None",
    "allergies": "None",
    "family_history": "None",
    "smoking": "Never",
    "alcohol": "Rarely",
    "language_instruction": "LANGUAGE & TONE: reply in English.",
}


def _chunk_dict(chunk: Any) -> dict[str, Any]:
    """Keep the shape-bearing fields and drop everything provider-internal."""
    recorded: dict[str, Any] = {
        "content": chunk.content,
        "tool_calls": getattr(chunk, "tool_calls", None) or [],
        "invalid_tool_calls": getattr(chunk, "invalid_tool_calls", None) or [],
        "tool_call_chunks": getattr(chunk, "tool_call_chunks", None) or [],
    }
    usage = getattr(chunk, "usage_metadata", None)
    if usage:
        recorded["usage_metadata"] = usage
    return recorded


async def _capture() -> dict[str, Any]:
    from preconsult.services.agent_service import get_interview_chain

    chain = get_interview_chain()
    chunks = [_chunk_dict(chunk) async for chunk in chain.astream(SYNTHETIC_INPUT)]

    from preconsult.core.config import LLM_PROVIDER

    return {
        "provider": LLM_PROVIDER,
        "source": "scripts/capture_llm_stream.py",
        "description": "Captured from a synthetic prompt; review before committing.",
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Path to write the fixture JSON")
    parser.add_argument(
        "--allow-fixtures",
        action="store_true",
        help="Permit writing under tests/fixtures/llm/ (review the output first)",
    )
    args = parser.parse_args()

    out = Path(args.out).resolve()
    if out.is_relative_to(FIXTURES_DIR) and not args.allow_fixtures:
        raise SystemExit(
            f"refusing to write into {FIXTURES_DIR} without --allow-fixtures"
        )

    payload = asyncio.run(_capture())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(payload['chunks'])} chunks to {out}")
    print("review the output for patient data or prompt text before committing")


if __name__ == "__main__":
    main()
