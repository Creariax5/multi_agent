"""Zapier Bridge Configuration"""
import os

# Zapier MCP Server URL - obtenue depuis mcp.zapier.com après configuration
# Format: https://mcp.zapier.com/api/mcp/mcp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ZAPIER_MCP_URL = os.getenv("ZAPIER_MCP_URL", "")

# Secret for Zapier MCP (Bearer token from embed config) - Optional for personal servers
ZAPIER_MCP_SECRET = os.getenv("ZAPIER_MCP_SECRET", "")

# Enable/disable Zapier integration - Only URL is required
ZAPIER_ENABLED = bool(ZAPIER_MCP_URL)
