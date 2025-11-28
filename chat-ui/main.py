"""
Chat UI - A ChatGPT-like interface using Copilot Proxy
"""
import os
import httpx
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://copilot-proxy:8080/v1")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    model = data.get("model", "gpt-4.1")
    use_tools = data.get("use_tools", True)
    
    async def generate():
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{COPILOT_PROXY_URL}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "use_tools": use_tools
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'error': f'API Error: {response.status_code}'})}\n\n"
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                chunk = json.loads(data_str)
                                
                                # Forward ALL event types to the frontend
                                event_type = chunk.get("type")
                                if event_type in ("tool_call", "thinking", "thinking_delta", 
                                                  "artifact", "artifact_edit", "history_update", "message_delta"):
                                    yield f"data: {json.dumps(chunk)}\n\n"
                                    continue
                                
                                # Forward message content (chat completion chunks)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    yield f"data: {json.dumps(chunk)}\n\n"
                            except json.JSONDecodeError:
                                pass
                        elif line.strip():
                            yield f"{line}\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            # OpenAI - modèles actuels
            {"id": "gpt-4.1", "name": "GPT-4.1", "provider": "openai"},
            {"id": "gpt-5", "name": "GPT-5", "provider": "openai"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai"},
            # Anthropic - modèles Claude actuels (3.5 retiré!)
            {"id": "claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "anthropic"},
            {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "provider": "anthropic"},
            {"id": "claude-opus-4.5", "name": "Claude Opus 4.5", "provider": "anthropic"},
            {"id": "claude-haiku-4.5", "name": "Claude Haiku 4.5", "provider": "anthropic"},
            # Google - modèles Gemini actuels
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "google"},
            {"id": "gemini-3-pro", "name": "Gemini 3 Pro", "provider": "google"},
            # xAI
            {"id": "grok-code-fast-1", "name": "Grok Code Fast", "provider": "xai"},
        ]
    }
