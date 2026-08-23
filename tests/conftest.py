import os

# Global test environment configuration
os.environ["PRECONSULT_API_KEY"] = "ci_test_key_123"
os.environ["GOOGLE_CLOUD_PROJECT"] = "securemed-chat-494521"
os.environ["GOOGLE_CLOUD_REGION"] = "us-east1"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


def _reset_session_service_state():
    """Reset the session-service module singleton state between tests.

    The service caches its Redis pool, a health latch and an in-memory rate
    limiter at module scope. Tests that force the memory fallback (by flipping
    ``_redis_available``) or exercise Redis leave these mutated, so a leaked
    value can make an unrelated test depend on ordering. Restoring them after
    every test makes the suite deterministic regardless of execution order.
    """
    import preconsult.services.session_service as srv

    srv._redis_pool = None
    srv._redis_available = None


def _reset_health_probe_cache():
    """Clear the /health throttle cache so mocked probes are seen by tests.

    The health endpoints cache their redis/event-channel statuses behind a TTL,
    so a mocked status from one test would otherwise be masked by a warm cache
    in the next.
    """
    try:
        import reflex_app.preconsult.preconsult as pcm

        pcm._reset_health_probe_cache_unlocked()
    except Exception:
        pass


def pytest_runtest_setup(item):
    _reset_session_service_state()
    _reset_health_probe_cache()


def pytest_runtest_teardown(item, nextitem):
    _reset_session_service_state()
    _reset_health_probe_cache()

