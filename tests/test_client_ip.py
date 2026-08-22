"""
Tests for the proxy-header trust policy behind client-IP resolution.

Spoofable ``cf-connecting-ip`` / ``x-forwarded-for`` headers must not feed
rate-limiting / quota keys unless the app is explicitly configured to trust a
fronting proxy (``TRUST_PROXY_HEADERS=true``). Otherwise an attacker could
rotate fake IPs to bypass per-IP limits.
"""

from starlette.requests import Request


def _make_request(headers=None, client_host="203.0.113.7"):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/session/init",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": ("203.0.113.7", 54321) if client_host else None,
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_spoofed_cf_header_ignored_by_default(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", False)
    req = _make_request(headers={"cf-connecting-ip": "6.6.6.6"})
    assert endpoints.get_client_ip(req) == "203.0.113.7"


def test_spoofed_xff_header_ignored_by_default(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", False)
    req = _make_request(headers={"x-forwarded-for": "6.6.6.6, 7.7.7.7"})
    assert endpoints.get_client_ip(req) == "203.0.113.7"


def test_real_client_host_used_when_no_proxy_header(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", False)
    req = _make_request(headers={})
    assert endpoints.get_client_ip(req) == "203.0.113.7"


def test_missing_client_falls_back_to_loopback(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", False)
    req = _make_request(headers={}, client_host=None)
    assert endpoints.get_client_ip(req) == "127.0.0.1"


def test_cf_header_honored_when_proxy_trusted(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    req = _make_request(headers={"cf-connecting-ip": "6.6.6.6"})
    assert endpoints.get_client_ip(req) == "6.6.6.6"


def test_xff_used_when_proxy_trusted_and_first_entry_preferred(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    req = _make_request(headers={"x-forwarded-for": "6.6.6.6, 10.0.0.1"})
    assert endpoints.get_client_ip(req) == "6.6.6.6"


def test_cf_header_takes_priority_over_xff_when_trusted(monkeypatch):
    from preconsult.api import endpoints

    monkeypatch.setattr(endpoints, "TRUST_PROXY_HEADERS", True)
    req = _make_request(headers={"cf-connecting-ip": "6.6.6.6", "x-forwarded-for": "9.9.9.9"})
    assert endpoints.get_client_ip(req) == "6.6.6.6"
