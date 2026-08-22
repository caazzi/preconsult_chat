"""
Pure helpers for parsing client-side context that is shared between the
Reflex frontend and backend.

Kept dependency-free so it can be unit-tested in isolation and reused by both
sides of the app without pulling in reflex or FastAPI.
"""

import re


def split_questions(buffer: str) -> list[str]:
    """Split an accumulated stream buffer into individual questions.

    Handles numbered (``1.``, ``1)``), dash-prefixed and plain newline-separated
    question lists. Mirrors the OPQRST/SAMPLE numbered format the LLM is
    instructed to emit.
    """
    qs = [q.strip() for q in re.split(r'\n(?:\d+[\.\)]|\-)\s*', '\n' + buffer) if q.strip()]
    if len(qs) <= 1:
        qs = [q.strip() for q in buffer.strip().split('\n') if q.strip()]
    return qs


_EMERGENCY_TRIGGERS = (
    "emergency",
    "911",
    "emergência",
    "emergencia",
    "urgência",
    "urgencia",
)


def is_emergency_trigger(text: str) -> bool:
    """Return True if the accumulated buffer signals an emergency red flag.

    Covers the English ``emergency``/``911`` and the Portuguese
    ``urgência``/``urgencia`` tokens the safety guardrails instruct the model to
    emit verbatim, independent of accent/diacritic encoding.
    """
    lower = text.lower()
    return any(token in lower for token in _EMERGENCY_TRIGGERS)
