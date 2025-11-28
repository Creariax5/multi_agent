"""
MCP Server client - Tools management and execution
"""
import json
import logging
from typing import Optional
import httpx
from src.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)

# Cache for MCP tools and metadata
_cached_tools = None
_cached_metas = None


async def get_mcp_tools() -> list:
    """Fetch available tools from MCP server"""
    global _cached_tools
    
    if _cached_tools:
        return _cached_tools
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/tools")
            if response.status_code == 200:
                data = response.json()
                _cached_tools = data.get("tools", [])
                logger.info(f"🛠️ Loaded {len(_cached_tools)} tools from MCP server")
                return _cached_tools
    except Exception as e:
        logger.error(f"❌ Failed to fetch MCP tools: {e}")
    
    return []


async def get_tool_handlers() -> dict:
    """Fetch tool handler info from MCP server"""
    global _cached_metas
    
    if _cached_metas is not None:
        return _cached_metas
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/tools/handlers")
            if response.status_code == 200:
                data = response.json()
                _cached_metas = data.get("handlers", {})
                return _cached_metas
    except Exception as e:
        logger.error(f"❌ Failed to fetch handlers: {e}")
    
    return {}


async def tool_to_event(name: str, args: dict, result: dict) -> Optional[dict]:
    """Ask MCP server to convert tool call to UI event"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/tools/to_event",
                json={"name": name, "arguments": args, "result": result}
            )
            if response.status_code == 200:
                return response.json().get("event")
    except:
        pass
    return None


async def execute_tool_calls(tool_calls: list) -> list:
    """Execute tool calls via MCP server"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/execute_batch",
                json={"tool_calls": tool_calls}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
    except Exception as e:
        logger.error(f"❌ Failed to execute tools: {e}")
        return [
            {
                "tool_call_id": tc.get("id", "unknown"),
                "role": "tool",
                "content": json.dumps({"error": str(e)})
            }
            for tc in tool_calls
        ]
    
    return []


def clear_cache():
    """Clear cached tools and handlers (useful for hot reload)"""
    global _cached_tools, _cached_metas
    _cached_tools = None
    _cached_metas = None
