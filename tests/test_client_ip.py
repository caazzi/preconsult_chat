"""Client-IP resolution, pinned to what Cloud Run actually sends.

Measured on 2026-10-26 against a header-echo service behind the same frontend
(see ``get_client_ip`` docstring):

| Client sends | Container receives |
|---|---|
| nothing | ``request.client.host`` = ``169.254.169.126``, ``x-forwarded-for: 187.15.85.23`` |
| ``X-Forwarded-For: 1.2.3.4`` | ``x-forwarded-for: 1.2.3.4,187.15.85.23`` |
| ``cf-connecting-ip: 5.6.7.8`` | ``cf-connecting-ip: 5.6.7.8`` (untouched) |

So the transport peer is one shared proxy address, Cloud Run *appends* the real
client as the **last** XFF hop without stripping forgeries, and
``cf-connecting-ip`` is entirely client-controlled on this DNS-only domain.
These tests pin that reading: a leftmost-hop regression would make the
per-IP session quota and rate limits spoofable, and a transport-only regression
would make them global.
"""

import pytest
from starlette.requests import Request

# The address every Cloud Run container sees as its peer.
CLOUDRUN_PEER = "169.254.169.126"
CLIENT = "187.15.85.23"


def _make_request(headers=None, client_host=CLOUDRUN_PEER):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/session/init",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": (client_host, 54321) if client_host else None,
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


@pytest.fixture
def endpoints():
    from preconsult.api import endpoints as module

    return module


@pytest.fixture
def trusting(endpoints, monkeypatch):
    """Proxy headers trusted, Cloudflare-only header still off (the default)."""
    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(endpoints, "TRUST_CF_CONNECTING_IP", False)
    return endpoints


@pytest.fixture
def untrusting(endpoints, monkeypatch):
    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr(endpoints, "TRUST_CF_CONNECTING_IP", False)
    return endpoints


# --------------------------------------------------------------------------
# Default: no proxy trust, headers are inert
# --------------------------------------------------------------------------
def test_spoofed_cf_header_ignored_by_default(untrusting):
    req = _make_request(headers={"cf-connecting-ip": "6.6.6.6"})
    assert untrusting.get_client_ip(req) == CLOUDRUN_PEER


def test_spoofed_xff_header_ignored_by_default(untrusting):
    req = _make_request(headers={"x-forwarded-for": f"6.6.6.6,{CLIENT}"})
    assert untrusting.get_client_ip(req) == CLOUDRUN_PEER


def test_missing_client_falls_back_to_loopback(untrusting):
    req = _make_request(headers={}, client_host=None)
    assert untrusting.get_client_ip(req) == "127.0.0.1"


# --------------------------------------------------------------------------
# Trusted proxy: only the hop the proxy appended is used
# --------------------------------------------------------------------------
def test_single_hop_is_the_client(trusting):
    req = _make_request(headers={"x-forwarded-for": CLIENT})
    assert trusting.get_client_ip(req) == CLIENT


def test_client_supplied_prefix_is_ignored(trusting):
    """The exact header Cloud Run produced for a forged request."""
    req = _make_request(headers={"x-forwarded-for": f"1.2.3.4,{CLIENT}"})
    assert trusting.get_client_ip(req) == CLIENT


def test_many_forged_entries_are_ignored(trusting):
    req = _make_request(headers={"x-forwarded-for": f"1.1.1.1, 2.2.2.2, {CLIENT}"})
    assert trusting.get_client_ip(req) == CLIENT


def test_trailing_whitespace_and_empty_hops_are_tolerated(trusting):
    req = _make_request(headers={"x-forwarded-for": f"1.1.1.1, , {CLIENT} "})
    assert trusting.get_client_ip(req) == CLIENT


def test_ipv6_client_is_supported(trusting):
    req = _make_request(headers={"x-forwarded-for": "1.1.1.1,2001:4ca0:108:42::24"})
    assert trusting.get_client_ip(req) == "2001:4ca0:108:42::24"


def test_invalid_last_hop_falls_back_to_transport(trusting):
    req = _make_request(headers={"x-forwarded-for": f"{CLIENT}, not-an-ip"})
    assert trusting.get_client_ip(req) == CLOUDRUN_PEER


def test_oversized_last_hop_is_rejected(trusting):
    req = _make_request(headers={"x-forwarded-for": f"{CLIENT}, " + "9" * 200})
    assert trusting.get_client_ip(req) == CLOUDRUN_PEER


def test_no_forwarded_header_falls_back_to_transport(trusting):
    req = _make_request(headers={})
    assert trusting.get_client_ip(req) == CLOUDRUN_PEER


# --------------------------------------------------------------------------
# cf-connecting-ip needs its own opt-in (Cloudflare is DNS-only here)
# --------------------------------------------------------------------------
def test_cf_header_is_ignored_even_when_proxy_trusted(trusting):
    req = _make_request(
        headers={"cf-connecting-ip": "6.6.6.6", "x-forwarded-for": CLIENT}
    )
    assert trusting.get_client_ip(req) == CLIENT


def test_cf_header_honored_only_with_its_own_flag(endpoints, monkeypatch):
    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(endpoints, "TRUST_CF_CONNECTING_IP", True)
    req = _make_request(
        headers={"cf-connecting-ip": "6.6.6.6", "x-forwarded-for": CLIENT}
    )
    assert endpoints.get_client_ip(req) == "6.6.6.6"


def test_malformed_cf_header_falls_through_to_xff(endpoints, monkeypatch):
    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(endpoints, "TRUST_CF_CONNECTING_IP", True)
    req = _make_request(
        headers={"cf-connecting-ip": "not-an-ip", "x-forwarded-for": CLIENT}
    )
    assert endpoints.get_client_ip(req) == CLIENT
