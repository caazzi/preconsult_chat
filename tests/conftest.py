import os

# Global test environment configuration
os.environ["PRECONSULT_API_KEY"] = "ci_test_key_123"
os.environ["GOOGLE_CLOUD_PROJECT"] = "ci_test_project"
os.environ["GOOGLE_CLOUD_REGION"] = "us-east1"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
