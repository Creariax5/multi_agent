"""MCP Server client - Tools management and execution"""
import json
import logging
from typing import Optional
import httpx
from src.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)

# Cache
_cache = {"tools": None, "handlers": None}


async def _mcp_request(method: str, path: str, json_data: dict = None, timeout: float = 10.0):
    """Helper for MCP server requests"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                resp = await client.get(f"{MCP_SERVER_URL}{path}")
            else:
                resp = await client.post(f"{MCP_SERVER_URL}{path}", json=json_data)
            return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ MCP request failed ({path}): {e}")
        return None


async def get_mcp_tools() -> list:
    """Fetch available tools from MCP server (no cache - always fresh)"""
    data = await _mcp_request("GET", "/tools")
    if data:
        tools = data.get("tools", [])
        logger.info(f"🛠️ Loaded {len(tools)} tools from MCP server")
        return tools
    return []


async def get_tool_handlers() -> dict:
    """Fetch tool handler info from MCP server (no cache - always fresh)"""
    data = await _mcp_request("GET", "/tools/handlers")
    return data.get("handlers", {}) if data else {}


async def tool_to_event(name: str, args: dict, result: dict) -> Optional[dict]:
    """Ask MCP server to convert tool call to UI event"""
    data = await _mcp_request("POST", "/tools/to_event", {"name": name, "arguments": args, "result": result}, 5.0)
    return data.get("event") if data else None


async def execute_tool_calls(tool_calls: list) -> list:
    """Execute tool calls via MCP server"""
    data = await _mcp_request("POST", "/execute_batch", {"tool_calls": tool_calls}, 30.0)
    if data:
        return data.get("results", [])
    return [{"tool_call_id": tc.get("id", "unknown"), "role": "tool", "content": json.dumps({"error": "MCP request failed"})} for tc in tool_calls]


def clear_cache():
    """Clear cached tools and handlers"""
    _cache["tools"] = None
    _cache["handlers"] = None
