"""
Simple Copilot Proxy - Exposes GitHub Copilot as OpenAI-compatible API
"""
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time

app = FastAPI()

GITHUB_COPILOT_TOKEN = os.getenv("COPILOT_TOKEN", "")
COPILOT_API_URL = "https://api.githubcopilot.com"

# Cache for the Copilot access token
cached_token = None
token_expires_at = 0


async def get_copilot_token():
    """Exchange GitHub OAuth token for Copilot API token"""
    global cached_token, token_expires_at
    
    # Return cached token if still valid
    if cached_token and time.time() < token_expires_at - 60:
        return cached_token
    
    if not GITHUB_COPILOT_TOKEN:
        raise HTTPException(status_code=500, detail="COPILOT_TOKEN not configured")
    
    async with httpx.AsyncClient() as client:
        # Get Copilot token from GitHub
        response = await client.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {GITHUB_COPILOT_TOKEN}",
                "Accept": "application/json",
                "User-Agent": "GithubCopilot/1.0"
            }
        )
        
        if response.status_code != 200:
            print(f"Failed to get Copilot token: {response.status_code} {response.text}")
            raise HTTPException(status_code=401, detail=f"Failed to get Copilot token: {response.text}")
        
        data = response.json()
        cached_token = data.get("token")
        token_expires_at = data.get("expires_at", time.time() + 1800)
        
        return cached_token


@app.get("/")
async def root():
    return {"status": "ok", "message": "Copilot Proxy is running"}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4", "object": "model", "owned_by": "github-copilot"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "github-copilot"},
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    print("Received chat completion request")
    try:
        body = await request.json()
        print(f"Request body: {json.dumps(body, indent=2)[:500]}")
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    copilot_token = await get_copilot_token()
    print(f"Got copilot token: {copilot_token[:20]}...")
    
    # Build request for Copilot API
    headers = {
        "Authorization": f"Bearer {copilot_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Editor-Version": "vscode/1.85.0",
        "Editor-Plugin-Version": "copilot-chat/0.12.0",
        "Openai-Organization": "github-copilot",
        "User-Agent": "GitHubCopilotChat/0.12.0",
    }
    
    # Forward to Copilot
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{COPILOT_API_URL}/chat/completions",
            headers=headers,
            json=body
        )
        
        if response.status_code != 200:
            print(f"Copilot API error: {response.status_code} {response.text}")
            return JSONResponse(
                status_code=response.status_code,
                content={"error": response.text}
            )
        
        result = response.json()
        
        # Log la réponse complète pour debug
        print(f"=" * 60)
        print(f"COPILOT RESPONSE:")
        print(f"  Requested model: {body.get('model', 'unknown')}")
        print(f"  Response model:  {result.get('model', 'NOT IN RESPONSE')}")
        print(f"  Response ID:     {result.get('id', 'N/A')}")
        print(f"  Created:         {result.get('created', 'N/A')}")
        if 'usage' in result:
            print(f"  Usage:           {result['usage']}")
        print(f"  Full response keys: {list(result.keys())}")
        print(f"=" * 60)
        
        return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "healthy"}
