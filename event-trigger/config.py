"""Event Trigger Configuration"""
import os

# Copilot Proxy URL for AI processing
COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080")

# Memory Service URL for user lookups
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8084")

# Default AI model
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4.1")

# Webhook secret for validation (optional)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
