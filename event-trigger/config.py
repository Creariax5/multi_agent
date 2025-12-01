"""Event Trigger Configuration"""
import os

# Copilot Proxy URL for AI processing
COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")

# Default AI model
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1")

# Webhook secret for validation (optional)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# Enable/disable specific sources
ENABLED_SOURCES = os.getenv("ENABLED_SOURCES", "email,stripe,slack,zapier,custom").split(",")
