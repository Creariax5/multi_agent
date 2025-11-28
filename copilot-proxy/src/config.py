"""
Configuration settings for Copilot Proxy
"""
import os

# GitHub Copilot settings
GITHUB_COPILOT_TOKEN = os.getenv("COPILOT_TOKEN", "")
COPILOT_API_URL = "https://api.githubcopilot.com"

# MCP Server settings
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8081")

# Model used for tool calls (FREE = no credits)
TOOL_CALL_MODEL = "gpt-4.1"

# Agentic loop settings
MAX_AGENTIC_ITERATIONS = 15
AUTO_SUMMARIZE_THRESHOLD = 10
