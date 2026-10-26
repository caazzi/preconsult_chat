"""
Per-session cookie signing (stdlib-only, no extra dependency).

The browser's session is authenticated by a signed, HttpOnly cookie whose value
is ``<session_id>.<hmac>``. The HMAC ties the opaque session id to the server
secret so a client cannot forge or tamper with another session's id. No PHI is
ever placed in the cookie — only the opaque id the session store already uses.

Kept dependency-free and pure so it is trivially unit-testable.
"""

import base64
import hashlib
import hmac

from preconsult.core.config import SESSION_SECRET


def secure_compare(a: str, b: str) -> bool:
    """Constant-time compare two strings, safe for attacker-supplied credentials.

    ``hmac.compare_digest`` raises ``TypeError`` when handed ``str`` values that
    contain non-ASCII characters (Starlette decodes headers/cookies as latin-1,
    so a raw byte ``>= 0x80`` reaches us as e.g. ``"caf\u00e9"``). Comparing the
    UTF-8 *bytes* keeps the comparison constant-time and never raises: a value
    that cannot be encoded (lone surrogate) simply does not match.
    """
    try:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
    except (TypeError, UnicodeError):
        return False


def _sign(value: str) -> str:
    digest = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_session_id(session_id: str) -> str:
    """Return a signed cookie value for ``session_id``."""
    return f"{session_id}.{_sign(session_id)}"


def verify_session_cookie(value: str | None) -> str | None:
    """Return the session id if the signature is valid, else ``None``.

    Uses constant-time comparison so a forged cookie cannot be discovered
    byte-by-byte from timing.
    """
    if not value or "." not in value:
        return None
    session_id, _, signature = value.rpartition(".")
    if not session_id:
        return None
    if not secure_compare(signature, _sign(session_id)):
        return None
    return session_id
