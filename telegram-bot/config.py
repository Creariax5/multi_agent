"""Configuration"""
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8482878750:AAGTDLoWZlJo379bHljvnf6ZamEE8Ned4kQ")
COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1")
