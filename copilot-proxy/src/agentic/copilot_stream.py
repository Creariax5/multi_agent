"""Parse SSE stream from Copilot API"""
import json
import httpx
from src.config import COPILOT_API_URL
from src.copilot import get_headers


async def stream_copilot(token: str, messages: list, body: dict):
    """
    Stream from Copilot API and yield parsed chunks.
    
    Yields: (chunk_type, data) tuples
        - ("tool_chunk", {index, id, name, arguments})
        - ("done", None)
        - ("error", status_code)
    """
    headers = get_headers(token, messages)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{COPILOT_API_URL}/chat/completions", headers=headers, json=body) as resp:
            if resp.status_code != 200:
                yield ("error", resp.status_code)
                return
            
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                
                data = line[6:].strip()
                if data == "[DONE]":
                    yield ("done", None)
                    return
                
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    
                    for tc in delta.get("tool_calls", []):
                        yield ("tool_chunk", {
                            "index": tc.get("index"),
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name"),
                            "arguments": tc.get("function", {}).get("arguments", "")
                        })
                except:
                    pass
    
    yield ("done", None)
