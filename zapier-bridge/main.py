"""
Zapier Bridge Server

This service acts as a bridge between your MCP server and Zapier MCP.
It provides a REST API that your mcp-server can call to:
1. List available Zapier tools
2. Execute Zapier tools

Configure ZAPIER_MCP_URL environment variable with the URL from Zapier MCP.
Get it from: https://mcp.zapier.com/
"""
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from zapier_client import zapier_client
from config import ZAPIER_ENABLED, ZAPIER_MCP_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    if ZAPIER_ENABLED:
        logger.info(f"🔗 Zapier MCP URL configured: {ZAPIER_MCP_URL[:60]}...")
    else:
        logger.warning("⚠️ Zapier MCP not configured. Set ZAPIER_MCP_URL.")
    yield
    # Shutdown
    await zapier_client.disconnect()


app = FastAPI(title="Zapier MCP Bridge", lifespan=lifespan)


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


@app.get("/")
async def root():
    """Health check"""
    connected = zapier_client._connected if hasattr(zapier_client, '_connected') else False
    return {
        "status": "ok",
        "zapier_enabled": ZAPIER_ENABLED,
        "zapier_connected": connected
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "zapier_enabled": ZAPIER_ENABLED}


@app.get("/tools")
async def get_tools():
    """
    Get available Zapier tools in OpenAI function format.
    This can be called by mcp-server to merge with local tools.
    """
    if not ZAPIER_ENABLED:
        return {"tools": [], "message": "Zapier not configured"}
    
    try:
        mcp_tools = await zapier_client.list_tools()
        openai_tools = zapier_client.get_tools_as_openai_format(mcp_tools)
        return {"tools": openai_tools, "count": len(openai_tools)}
    except Exception as e:
        logger.error(f"Error getting Zapier tools: {e}")
        return {"tools": [], "error": str(e)}


@app.get("/tools/raw")
async def get_raw_tools():
    """Get raw MCP tools format"""
    if not ZAPIER_ENABLED:
        return {"tools": []}
    
    tools = await zapier_client.list_tools()
    return {"tools": tools}


@app.post("/execute")
async def execute_tool(request: ToolCallRequest):
    """
    Execute a Zapier tool.
    Tool name should include 'zapier_' prefix which will be stripped.
    """
    if not ZAPIER_ENABLED:
        raise HTTPException(status_code=503, detail="Zapier not configured")
    
    # Strip zapier_ prefix if present
    tool_name = request.name
    if tool_name.startswith("zapier_"):
        tool_name = tool_name[7:]
    
    logger.info(f"⚡ Executing Zapier tool: {tool_name}")
    
    result = await zapier_client.call_tool(tool_name, request.arguments)
    
    if result.get("success"):
        return {"tool": request.name, "result": result.get("result")}
    else:
        return {"tool": request.name, "error": result.get("error")}


@app.post("/refresh")
async def refresh_tools():
    """Force refresh of tools cache"""
    zapier_client.clear_cache()
    if ZAPIER_ENABLED:
        await zapier_client.initialize()
        tools = await zapier_client.list_tools()
        return {"status": "refreshed", "tools_count": len(tools)}
    return {"status": "zapier_disabled"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
