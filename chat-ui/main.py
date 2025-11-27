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
    model = data.get("model", "gpt-4")
    
    async def generate():
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{COPILOT_PROXY_URL}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    yield json.dumps({"error": f"API Error: {response.status_code}"})
                    return
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                yield json.dumps({"content": content})
                
            except Exception as e:
                yield json.dumps({"error": str(e)})
    
    return StreamingResponse(generate(), media_type="application/json")


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
