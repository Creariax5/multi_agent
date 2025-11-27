"""
MCP Server - Plugin-based Tools System
Each tool is a separate file in the tools/ directory
"""
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from tools import load_all_tools

app = FastAPI(title="MCP Tools Server")

# Load tools at startup
print("Loading MCP tools...")
TOOLS, FUNCTIONS, HANDLERS = load_all_tools()
print(f"Loaded {len(TOOLS)} tools")


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
    return {"status": "ok", "tools": list(FUNCTIONS.keys())}


@app.get("/tools")
async def get_tools():
    """Return tool definitions"""
    return {"tools": TOOLS}


@app.get("/tools/handlers")
async def get_handlers():
    """Return tool handler info (to_event, is_terminal)"""
    info = {}
    for name, module in HANDLERS.items():
        info[name] = {
            "has_to_event": hasattr(module, "to_event"),
            "is_terminal": getattr(module, "is_terminal", lambda: False)()
        }
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
    """Execute a single tool"""
    if request.name not in FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Tool '{request.name}' not found")
    
    try:
        result = FUNCTIONS[request.name](**request.arguments)
        return {"tool": request.name, "result": result}
    except Exception as e:
        return {"tool": request.name, "error": str(e)}


@app.post("/execute_batch")
async def execute_batch(request: ToolCallBatchRequest):
    """Execute multiple tool calls"""
    results = []
    
    for tc in request.tool_calls:
        tool_id = tc.get("id", "unknown")
        func = tc.get("function", {})
        name = func.get("name", "")
        
        try:
            args = json.loads(func.get("arguments", "{}"))
        except:
            args = {}
        
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
    return {"status": "healthy", "tools": len(FUNCTIONS)}
