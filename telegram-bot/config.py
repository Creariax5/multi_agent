"""Configuration"""
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8084")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1")
