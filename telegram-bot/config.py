"""Configuration"""
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1")
