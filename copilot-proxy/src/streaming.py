"""
SSE Streaming utilities
"""
import json
import logging

logger = logging.getLogger(__name__)


def format_sse_event(event: dict) -> str:
    """Format an event as SSE data line"""
    return f"data: {json.dumps(event)}\n\n"


def format_content_chunk(content: str) -> str:
    """Format a content chunk as OpenAI-compatible SSE"""
    chunk = {
        "id": "agentic",
        "object": "chat.completion.chunk",
        "choices": [{
            "index": 0,
            "delta": {"content": content},
            "finish_reason": None
        }]
    }
    return f"data: {json.dumps(chunk)}\n\n"


def format_done_chunk() -> str:
    """Format the final done chunk"""
    done_chunk = {
        "id": "agentic",
        "object": "chat.completion.chunk",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    return f"data: {json.dumps(done_chunk)}\n\ndata: [DONE]\n\n"


async def stream_agentic_events(agentic_generator):
    """
    Convert agentic loop events to SSE stream.
    
    Args:
        agentic_generator: Async generator from run_agentic_loop
        
    Yields:
        SSE formatted strings
    """
    async for event in agentic_generator:
        event_type = event.get("type")
        logger.debug(f"Streaming: {event_type}")
        
        if event_type == "model_info":
            yield format_sse_event({
                "type": "model_info",
                "model": event["model"]
            })
        
        elif event_type == "tool_call":
            yield format_sse_event({
                "type": "tool_call",
                "tool_call": event["tool_call"]
            })
        
        elif event_type == "thinking":
            yield format_sse_event({
                "type": "thinking",
                "content": event["content"]
            })
        
        elif event_type == "thinking_delta":
            yield format_sse_event({
                "type": "thinking_delta",
                "content": event["content"]
            })
        
        elif event_type == "artifact":
            logger.info(f"🎨 Artifact: {event.get('title')}")
            yield format_sse_event({
                "type": "artifact",
                "content": event["content"],
                "title": event["title"],
                "artifact_type": event["artifact_type"]
            })
        
        elif event_type == "artifact_edit":
            logger.info(f"✏️ Artifact edit: {event.get('description')}")
            yield format_sse_event({
                "type": "artifact_edit",
                "selector": event["selector"],
                "operation": event["operation"],
                "content": event.get("content", ""),
                "attribute": event.get("attribute", ""),
                "description": event["description"]
            })
        
        elif event_type in ("message_delta", "message"):
            yield format_content_chunk(event["content"])
        
        elif event_type == "history_update":
            yield format_sse_event({
                "type": "history_update",
                "messages": event["messages"]
            })
    
    # Send done signal
    yield format_done_chunk()
