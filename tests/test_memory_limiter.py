"""The in-memory rate-limit fallback must stay bounded.

It is the last line of defence when Redis is unreachable or its daily quota is
spent, and its keys are per client IP. Until the client-IP fix those keys were
effectively one value; now they vary per visitor, so a cap is load-bearing:
without it a long outage grows a worker's dict for as long as it lives, because
expired counters were only dropped when the exact same key came back.
"""

import pytest

from preconsult.services import session_service


class _Clock:
    """Stand-in for the ``time`` module so expiry is controllable."""

    def __init__(self, now: float = 1000.0):
        self.now = now

    def monotonic(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = _Clock()
    monkeypatch.setattr(session_service, "time", fake)
    return fake


@pytest.fixture
def store():
    return session_service.MemoryRateLimitStore(max_keys=3)


@pytest.mark.asyncio
async def test_counter_increments_within_the_window(store, clock):
    assert await store.incr("rate_limit:a", 60) == 1
    assert await store.incr("rate_limit:a", 60) == 2
    assert await store.get("rate_limit:a") == 2


@pytest.mark.asyncio
async def test_counter_restarts_after_the_window(store, clock):
    await store.incr("rate_limit:a", 60)
    clock.now += 61

    assert await store.incr("rate_limit:a", 60) == 1


@pytest.mark.asyncio
async def test_expired_entries_do_not_hold_capacity(store, clock):
    """A burst of one-shot clients must not lock out later ones."""
    for i in range(3):
        await store.incr(f"rate_limit:old{i}", 60)
    assert len(store._store) == 3

    clock.now += 61
    await store.incr("rate_limit:new", 60)

    assert len(store._store) == 1
    assert "rate_limit:new" in store._store


@pytest.mark.asyncio
async def test_store_never_exceeds_the_cap(store, clock):
    for i in range(50):
        await store.incr(f"rate_limit:{i}", 86400)
        # Same instant, so nothing expires: eviction is the only way out.
        assert len(store._store) <= 3


@pytest.mark.asyncio
async def test_eviction_keeps_the_newest_key(store, clock):
    for i in range(3):
        await store.incr(f"rate_limit:{i}", 86400)

    await store.incr("rate_limit:fresh", 86400)

    assert "rate_limit:fresh" in store._store
    assert len(store._store) == 3


@pytest.mark.asyncio
async def test_get_drops_an_expired_key(store, clock):
    await store.incr("rate_limit:a", 60)
    clock.now += 61

    assert await store.get("rate_limit:a") is None
    assert store._store == {}


@pytest.mark.asyncio
async def test_clear_empties_the_store(store, clock):
    await store.incr("rate_limit:a", 60)
    await store.clear()

    assert store._store == {}


@pytest.mark.asyncio
async def test_zero_capacity_does_not_loop_forever(clock):
    tiny = session_service.MemoryRateLimitStore(max_keys=0)

    assert await tiny.incr("rate_limit:a", 60) == 1
