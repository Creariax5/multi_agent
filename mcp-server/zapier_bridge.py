"""
Zapier Bridge Client - Called by MCP Server to get Zapier tools
"""
import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

ZAPIER_BRIDGE_URL = os.getenv("ZAPIER_BRIDGE_URL", "http://zapier-bridge:8082")


class ZapierBridge:
    """Client for Zapier Bridge service"""
    
    def __init__(self):
        self.url = ZAPIER_BRIDGE_URL
        # No caching - always fetch fresh to avoid stale state after restarts
        self._tools_cache: Optional[List[Dict]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 60  # Cache for 60 seconds only
    
    async def _request(self, method: str, path: str, json_data: dict = None) -> Optional[Dict]:
        """Make request to Zapier Bridge"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.url}{path}"
                if method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json=json_data)
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.error(f"Zapier Bridge error: {resp.status_code}")
                    return None
        except Exception as e:
            logger.debug(f"Zapier Bridge not available: {e}")
            return None
    
    async def is_enabled(self) -> bool:
        """Check if Zapier Bridge is enabled and connected (no cache - always fresh check)"""
        result = await self._request("GET", "/")
        if result:
            return result.get("zapier_enabled", False) and result.get("zapier_connected", False)
        return False
    
    async def get_tools(self) -> List[Dict]:
        """Get Zapier tools in OpenAI format with TTL cache"""
        import time
        
        # Use cache only if fresh (within TTL)
        if self._tools_cache is not None and (time.time() - self._cache_time) < self._cache_ttl:
            return self._tools_cache
        
        if not await self.is_enabled():
            self._tools_cache = []
            self._cache_time = time.time()
            return []
        
        result = await self._request("GET", "/tools")
        if result:
            self._tools_cache = result.get("tools", [])
            self._cache_time = time.time()
            if self._tools_cache:
                logger.info(f"⚡ Loaded {len(self._tools_cache)} Zapier tools")
            return self._tools_cache
        return []
    
    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Zapier tool"""
        result = await self._request("POST", "/execute", {
            "name": name,
            "arguments": arguments
        })
        
        if result:
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result.get("result", "")}
        
        return {"success": False, "error": "Zapier Bridge not available"}
    
    def clear_cache(self):
        """Clear tools cache"""
        self._tools_cache = None
        self._cache_time = 0


# Singleton
zapier_bridge = ZapierBridge()
