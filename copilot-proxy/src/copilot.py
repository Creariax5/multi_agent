"""GitHub Copilot API client"""
import time
import logging
import httpx
from fastapi import HTTPException
from src.config import GITHUB_COPILOT_TOKEN, COPILOT_API_URL

logger = logging.getLogger(__name__)

# Token cache
_token = {"value": None, "expires": 0}


async def get_token() -> str:
    """Get Copilot API token (cached)"""
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    
    if not GITHUB_COPILOT_TOKEN:
        raise HTTPException(500, "COPILOT_TOKEN not configured")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={"Authorization": f"token {GITHUB_COPILOT_TOKEN}", "Accept": "application/json", "User-Agent": "GithubCopilot/1.0"}
        )
        
        if resp.status_code != 200:
            logger.error(f"❌ Token error: {resp.status_code}")
            raise HTTPException(401, f"Failed to get Copilot token: {resp.text}")
        
        data = resp.json()
        _token["value"] = data.get("token")
        _token["expires"] = data.get("expires_at", time.time() + 1800)
        return _token["value"]


def get_headers(token: str, messages: list, stream: bool = True) -> dict:
    """Build Copilot API headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        "Editor-Version": "vscode/1.103.2",
        "Copilot-Integration-Id": "vscode-chat",
        "X-Initiator": "agent" if any(m.get("role") == "tool" for m in messages) else "user",
        "x-github-api-version": "2025-05-01",
        "User-Agent": "GitHubCopilotChat/0.12.0",
    }


async def make_request(body: dict, token: str) -> dict | None:
    """Make non-streaming request to Copilot API"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{COPILOT_API_URL}/chat/completions", headers=get_headers(token, body.get("messages", []), False), json=body)
        return resp.json() if resp.status_code == 200 else None
