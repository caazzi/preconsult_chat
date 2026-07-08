"""
Centralized configuration management for the PreConsult application.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "preconsult")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-east1")
VERTEX_REGION = os.environ.get("VERTEX_AI_REGION", "us-central1")

BUILD_MODE = os.environ.get("BUILD_MODE") == "true"

PRECONSULT_API_KEY = os.environ.get("PRECONSULT_API_KEY")
if not PRECONSULT_API_KEY:
    if BUILD_MODE:
        logging.warning("BUILD_MODE=true: PRECONSULT_API_KEY nao verificada. NAO use em producao.")
    else:
        raise ValueError("FATAL: PRECONSULT_API_KEY nao definida. Abortando startup.")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

LLM_MODEL = "gemini-2.5-flash-lite"
