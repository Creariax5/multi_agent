"""Client for Copilot Proxy API"""
import json
import httpx
from config import COPILOT_PROXY_URL, DEFAULT_MODEL


async def chat(messages: list, model: str = None, user_context: dict = None) -> dict:
    """
    Send chat request to copilot-proxy and parse SSE response.
    
    Returns: {
        "messages": ["text1", "text2"],
        "thinking": ["thought1"],
        "artifacts": [{"title": "...", "content": "..."}]
    }
    """
    result = {"messages": [], "thinking": [], "artifacts": [], "tool_calls": []}
    
    async for event in chat_stream(messages, model, user_context):
        t = event.get("type")
        if t == "message":
            result["messages"].append(event["content"])
        elif t == "thinking":
            result["thinking"].append(event["content"])
        elif t == "artifact":
            result["artifacts"].append(event)
        elif t == "tool_call":
            result["tool_calls"].append(event)
    
    return result


async def chat_stream(messages: list, model: str = None, user_context: dict = None):
    """
    Stream chat events from copilot-proxy.
    
    Yields events: {"type": "thinking|message|artifact|tool_call", ...}
    """
    body = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": True,
        "use_tools": True
    }
    
    # Add user context for tools that need it (e.g., telegram_chat_id)
    if user_context:
        body["user_context"] = user_context
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{COPILOT_PROXY_URL}/v1/chat/completions", json=body) as resp:
            if resp.status_code != 200:
                yield {"type": "error", "content": f"Error: {resp.status_code}"}
                return
            
            buffer = {"message": "", "thinking": ""}
            
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                
                try:
                    event = json.loads(data)
                    t = event.get("type")
                    
                    # Message content (OpenAI format)
                    if "choices" in event:
                        delta = event["choices"][0].get("delta", {})
                        if "content" in delta:
                            buffer["message"] += delta["content"]
                    
                    # Thinking (full)
                    elif t == "thinking":
                        # Flush any buffered thinking first
                        if buffer["thinking"]:
                            yield {"type": "thinking", "content": buffer["thinking"]}
                            buffer["thinking"] = ""
                        yield {"type": "thinking", "content": event["content"]}
                    
                    # Thinking delta (streaming)
                    elif t == "thinking_delta":
                        buffer["thinking"] += event["content"]
                    
                    # Message (full)
                    elif t == "message":
                        yield {"type": "message", "content": event["content"]}
                    
                    # Tool call
                    elif t == "tool_call":
                        # Flush buffered thinking before tool call
                        if buffer["thinking"]:
                            yield {"type": "thinking", "content": buffer["thinking"]}
                            buffer["thinking"] = ""
                        yield {"type": "tool_call", "tool_call": event.get("tool_call", {})}
                    
                    # Artifact
                    elif t == "artifact":
                        yield {
                            "type": "artifact",
                            "title": event.get("title", "Artifact"),
                            "content": event.get("content", ""),
                            "artifact_type": event.get("artifact_type", "text")
                        }
                
                except json.JSONDecodeError:
                    pass
            
            # Flush remaining buffers
            if buffer["thinking"]:
                yield {"type": "thinking", "content": buffer["thinking"]}
            if buffer["message"]:
                yield {"type": "message", "content": buffer["message"]}


async def get_models() -> list:
    """Get available models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{COPILOT_PROXY_URL}/v1/models")
            if resp.status_code == 200:
                return resp.json().get("data", [])
    except:
        pass
    return []
