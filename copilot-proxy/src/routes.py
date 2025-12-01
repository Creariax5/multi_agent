"""
FastAPI route handlers
"""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from src.auth import get_copilot_token
from src.mcp_client import get_mcp_tools, get_tool_handlers, clear_cache
from src.messages import clean_messages
from src.agentic_loop import run_agentic_loop
from src.streaming import stream_agentic_events

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Copilot Proxy with MCP Tools is running"}


@router.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@router.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            # Free models (0x)
            {"id": "gpt-4.1", "object": "model", "owned_by": "github-copilot", "cost": "0x"},
            {"id": "gpt-4o", "object": "model", "owned_by": "github-copilot", "cost": "0x"},
            {"id": "gpt-5-mini", "object": "model", "owned_by": "github-copilot", "cost": "0x"},
            {"id": "grok-code-fast-1", "object": "model", "owned_by": "github-copilot", "cost": "0x"},
            {"id": "raptor-mini", "object": "model", "owned_by": "github-copilot", "cost": "0x"},
            # Premium models
            {"id": "claude-haiku-4.5", "object": "model", "owned_by": "github-copilot", "cost": "0.33x"},
            {"id": "claude-opus-4.5", "object": "model", "owned_by": "github-copilot", "cost": "1x"},
            {"id": "claude-sonnet-4", "object": "model", "owned_by": "github-copilot", "cost": "1x"},
            {"id": "claude-sonnet-4.5", "object": "model", "owned_by": "github-copilot", "cost": "1x"},
            {"id": "gemini-2.5-pro", "object": "model", "owned_by": "github-copilot", "cost": "1x"},
            {"id": "gemini-3-pro", "object": "model", "owned_by": "github-copilot", "cost": "1x"},
        ]
    }


@router.get("/v1/tools")
async def list_tools():
    """Get available MCP tools"""
    tools = await get_mcp_tools()
    return {"tools": tools, "count": len(tools)}


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Chat completions with AGENTIC tool handling"""
    logger.info("=" * 50)
    logger.info("📩 Chat completion request (AGENTIC MODE)")
    
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    messages = clean_messages(body.get("messages", []))
    copilot_token = await get_copilot_token()
    
    original_model = body.get("model", "gpt-4.1")
    use_tools = body.get("use_tools", True)
    stream = body.get("stream", False)
    
    logger.info(f"Model: {original_model} | Tools: {use_tools} | Stream: {stream}")
    
    # Get MCP tools
    mcp_tools, tool_handlers = [], {}
    if use_tools:
        mcp_tools = await get_mcp_tools()
        tool_handlers = await get_tool_handlers()
        if mcp_tools:
            logger.info(f"🔧 Loaded {len(mcp_tools)} MCP tools")
    
    # Run agentic loop
    agentic_gen = run_agentic_loop(
        messages=messages,
        copilot_token=copilot_token,
        mcp_tools=mcp_tools,
        tool_handlers=tool_handlers,
        use_tools=use_tools,
        model=original_model
    )
    
    if stream:
        return StreamingResponse(
            stream_agentic_events(agentic_gen),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    # Non-streaming: collect all events
    events = []
    async for event in agentic_gen:
        events.append(event)
    
    all_messages = [e["content"] for e in events if e.get("type") == "message"]
    all_tool_calls = [e["tool_call"] for e in events if e.get("type") == "tool_call"]
    
    result = {
        "id": "agentic",
        "object": "chat.completion",
        "model": original_model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "\n\n".join(all_messages)},
            "finish_reason": "stop"
        }],
        "events": events
    }
    if all_tool_calls:
        result["tool_calls_executed"] = all_tool_calls
    
    return JSONResponse(content=result)
