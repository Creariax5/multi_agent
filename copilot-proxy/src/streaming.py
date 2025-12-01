"""SSE Streaming utilities"""
import json

def sse(event: dict) -> str:
    """Format event as SSE"""
    return f"data: {json.dumps(event)}\n\n"


def sse_content(content: str) -> str:
    """Format content chunk as OpenAI-compatible SSE"""
    return sse({"id": "agentic", "object": "chat.completion.chunk", 
                "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]})


def sse_done() -> str:
    """Format done signal"""
    return sse({"id": "agentic", "object": "chat.completion.chunk", 
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}) + "data: [DONE]\n\n"


# Events that pass through as-is
PASSTHROUGH = {"model_info", "tool_call", "thinking", "thinking_delta", "history_update", "artifact", "artifact_edit"}


async def stream_agentic_events(gen):
    """Convert agentic events to SSE stream"""
    async for event in gen:
        t = event.get("type")
        if t in PASSTHROUGH:
            yield sse(event)
        elif t in ("message_delta", "message"):
            yield sse_content(event["content"])
    yield sse_done()
