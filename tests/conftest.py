import os
import pytest

# Global test environment configuration
# Setting these before anything else ensures modules that import core.config don't crash
os.environ["PRECONSULT_API_KEY"] = "ci_test_key_123"
os.environ["GOOGLE_CLOUD_PROJECT"] = "ci_test_project"
os.environ["GOOGLE_CLOUD_REGION"] = "us-east1"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

@pytest.fixture(autouse=True)
def reset_redis_pool():
    from preconsult.services import session_service
    session_service._redis_pool = None
    session_service._redis_available = None
    session_service._memory_limiter.clear()
    yield
    session_service._redis_pool = None
    session_service._redis_available = None
    session_service._memory_limiter.clear()
