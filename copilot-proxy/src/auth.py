"""
GitHub Copilot authentication and token management
"""
import time
import logging
import httpx
from fastapi import HTTPException

from src.config import GITHUB_COPILOT_TOKEN, COPILOT_API_URL

logger = logging.getLogger(__name__)

# Cache for the Copilot access token
_cached_token = None
_token_expires_at = 0


async def get_copilot_token() -> str:
    """Exchange GitHub OAuth token for Copilot API token"""
    global _cached_token, _token_expires_at
    
    # Return cached token if still valid
    if _cached_token and time.time() < _token_expires_at - 60:
        return _cached_token
    
    if not GITHUB_COPILOT_TOKEN:
        raise HTTPException(status_code=500, detail="COPILOT_TOKEN not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {GITHUB_COPILOT_TOKEN}",
                "Accept": "application/json",
                "User-Agent": "GithubCopilot/1.0"
            }
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to get Copilot token: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=401, 
                detail=f"Failed to get Copilot token: {response.text}"
            )
        
        data = response.json()
        _cached_token = data.get("token")
        _token_expires_at = data.get("expires_at", time.time() + 1800)
        
        return _cached_token


async def make_copilot_request(body: dict, copilot_token: str, stream: bool = False):
    """Make a request to Copilot API"""
    is_tool_continuation = any(
        msg.get("role") == "tool" for msg in body.get("messages", [])
    )
    initiator = "agent" if is_tool_continuation else "user"
    
    headers = {
        "Authorization": f"Bearer {copilot_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        "Editor-Version": "vscode/1.103.2",
        "Copilot-Integration-Id": "vscode-chat",
        "X-Initiator": initiator,
        "x-github-api-version": "2025-05-01",
        "User-Agent": "GitHubCopilotChat/0.12.0",
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{COPILOT_API_URL}/chat/completions",
            headers=headers,
            json=body
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Copilot API error: {response.status_code} {response.text}")
            return None
        
        return response.json()


def get_copilot_headers(copilot_token: str, messages: list) -> dict:
    """Build headers for Copilot API request"""
    is_tool_continuation = any(
        msg.get("role") == "tool" for msg in messages
    )
    initiator = "agent" if is_tool_continuation else "user"
    
    return {
        "Authorization": f"Bearer {copilot_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Editor-Version": "vscode/1.103.2",
        "Copilot-Integration-Id": "vscode-chat",
        "X-Initiator": initiator,
        "x-github-api-version": "2025-05-01",
        "User-Agent": "GitHubCopilotChat/0.12.0",
    }
