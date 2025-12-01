"""
MCP Server - Plugin-based Tools System
Each tool is a separate file in the tools/ directory
Supports Zapier MCP integration via zapier-bridge service
"""
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from tools import load_all_tools
from zapier_bridge import zapier_bridge

app = FastAPI(title="MCP Tools Server")

# Load local tools at startup
print("Loading MCP tools...")
TOOLS, FUNCTIONS, HANDLERS = load_all_tools()
print(f"Loaded {len(TOOLS)} local tools")


# ============================================================================
# API
# ============================================================================

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCallBatchRequest(BaseModel):
    tool_calls: List[Dict[str, Any]]


@app.get("/")
async def root():
    zapier_tools = await zapier_bridge.get_tools()
    all_tool_names = list(FUNCTIONS.keys()) + [t["function"]["name"] for t in zapier_tools]
    return {"status": "ok", "tools": all_tool_names, "local": len(FUNCTIONS), "zapier": len(zapier_tools)}


@app.get("/tools")
async def get_tools():
    """Return all tool definitions (local + Zapier)"""
    zapier_tools = await zapier_bridge.get_tools()
    return {"tools": TOOLS + zapier_tools}


@app.get("/tools/local")
async def get_local_tools():
    """Return only local tool definitions"""
    return {"tools": TOOLS}


@app.get("/tools/zapier")
async def get_zapier_tools():
    """Return only Zapier tool definitions"""
    zapier_tools = await zapier_bridge.get_tools()
    return {"tools": zapier_tools, "enabled": await zapier_bridge.is_enabled()}


@app.get("/tools/handlers")
async def get_handlers():
    """Return tool handler info (to_event, is_terminal)"""
    info = {}
    for name, module in HANDLERS.items():
        info[name] = {
            "has_to_event": hasattr(module, "to_event"),
            "is_terminal": getattr(module, "is_terminal", lambda: False)()
        }
    # Add Zapier tools (no special handlers)
    zapier_tools = await zapier_bridge.get_tools()
    for tool in zapier_tools:
        name = tool["function"]["name"]
        info[name] = {"has_to_event": False, "is_terminal": False}
    return {"handlers": info}


@app.post("/tools/to_event")
async def to_event(request: dict):
    """Transform a tool call into a UI event using the tool's to_event()"""
    name = request.get("name")
    args = request.get("arguments", {})
    result = request.get("result", {})
    
    if name not in HANDLERS:
        return {"event": None}
    
    module = HANDLERS[name]
    if hasattr(module, "to_event"):
        event = module.to_event(args, result)
        return {"event": event}
    
    return {"event": None}


@app.post("/execute")
async def execute_tool(request: ToolCallRequest):
    """Execute a single tool (local or Zapier)"""
    # Check if it's a Zapier tool
    if request.name.startswith("zapier_"):
        result = await zapier_bridge.execute(request.name, request.arguments)
        if result.get("success"):
            return {"tool": request.name, "result": result.get("result")}
        else:
            return {"tool": request.name, "error": result.get("error")}
    
    # Local tool
    if request.name not in FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Tool '{request.name}' not found")
    
    try:
        result = FUNCTIONS[request.name](**request.arguments)
        return {"tool": request.name, "result": result}
    except Exception as e:
        return {"tool": request.name, "error": str(e)}


@app.post("/execute_batch")
async def execute_batch(request: ToolCallBatchRequest):
    """Execute multiple tool calls (local and Zapier)"""
    results = []
    
    for tc in request.tool_calls:
        tool_id = tc.get("id", "unknown")
        func = tc.get("function", {})
        name = func.get("name", "")
        
        try:
            args = json.loads(func.get("arguments", "{}"))
        except:
            args = {}
        
        # Check if Zapier tool
        if name.startswith("zapier_"):
            result = await zapier_bridge.execute(name, args)
            if result.get("success"):
                results.append({"tool_call_id": tool_id, "role": "tool", "content": json.dumps(result.get("result", ""))})
            else:
                results.append({"tool_call_id": tool_id, "role": "tool", "content": json.dumps({"error": result.get("error")})})
            continue
        
        # Local tool
        if name not in FUNCTIONS:
            results.append({"tool_call_id": tool_id, "role": "tool", "content": json.dumps({"error": "Not found"})})
            continue
        
        try:
            result = FUNCTIONS[name](**args)
            results.append({"tool_call_id": tool_id, "role": "tool", "content": json.dumps(result)})
        except Exception as e:
            results.append({"tool_call_id": tool_id, "role": "tool", "content": json.dumps({"error": str(e)})})
    
    return {"results": results}


@app.get("/health")
async def health():
    zapier_enabled = await zapier_bridge.is_enabled()
    zapier_count = len(await zapier_bridge.get_tools()) if zapier_enabled else 0
    return {
        "status": "healthy", 
        "local_tools": len(FUNCTIONS),
        "zapier_tools": zapier_count,
        "zapier_enabled": zapier_enabled
    }


@app.post("/zapier/refresh")
async def refresh_zapier():
    """Force refresh Zapier tools cache"""
    zapier_bridge.clear_cache()
    tools = await zapier_bridge.get_tools()
    return {"status": "refreshed", "tools": len(tools)}
