"""FastAPI route handlers"""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from src.copilot import get_token
from src.mcp_client import get_mcp_tools, get_tool_handlers
from src.messages import clean_messages
from src.agentic import run_agentic_loop
from src.streaming import stream_agentic_events

logger = logging.getLogger(__name__)
router = APIRouter()

# Available models
MODELS = [
    {"id": "gpt-4.1", "cost": "0x"}, {"id": "gpt-4o", "cost": "0x"},
    {"id": "gpt-5-mini", "cost": "0x"}, {"id": "grok-code-fast-1", "cost": "0x"},
    {"id": "claude-sonnet-4", "cost": "1x"}, {"id": "gemini-2.5-pro", "cost": "1x"},
]


@router.get("/")
async def root():
    return {"status": "ok", "message": "Copilot Proxy with MCP Tools"}


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": m["id"], "object": "model", "owned_by": "github-copilot", "cost": m["cost"]} for m in MODELS]}


@router.get("/v1/tools")
async def list_tools():
    tools = await get_mcp_tools()
    return {"tools": tools, "count": len(tools)}


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Chat completions with agentic tool handling"""
    try:
        body = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON")
    
    messages = clean_messages(body.get("messages", []))
    token = await get_token()
    model = body.get("model", "gpt-4.1")
    use_tools = body.get("use_tools", True)
    stream = body.get("stream", False)
    
    logger.info(f"📩 Chat: {model} | tools={use_tools} | stream={stream}")
    
    mcp_tools, handlers = (await get_mcp_tools(), await get_tool_handlers()) if use_tools else ([], {})
    
    gen = run_agentic_loop(messages, token, mcp_tools, handlers, use_tools, model)
    
    if stream:
        return StreamingResponse(stream_agentic_events(gen), media_type="text/event-stream", 
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
    
    # Non-streaming
    events = [e async for e in gen]
    return JSONResponse({
        "id": "agentic", "object": "chat.completion", "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\n".join(e["content"] for e in events if e.get("type") == "message")}, "finish_reason": "stop"}],
        "events": events
    })
