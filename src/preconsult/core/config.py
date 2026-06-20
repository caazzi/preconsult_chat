"""
Centralized configuration management for the PreConsult application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "preconsult")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-east1")
VERTEX_REGION = os.environ.get("VERTEX_AI_REGION", "us-central1")

PRECONSULT_API_KEY = os.environ.get("PRECONSULT_API_KEY")
if not PRECONSULT_API_KEY and os.environ.get("BUILD_MODE") != "true":
    raise ValueError("FATAL: PRECONSULT_API_KEY environment variable not set. Aborting startup.")

LLM_MODEL = "gemini-2.5-flash-lite"
