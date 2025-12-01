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
        self._tools_cache: Optional[List[Dict]] = None
        self._enabled: Optional[bool] = None
    
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
        """Check if Zapier Bridge is enabled and connected"""
        if self._enabled is not None:
            return self._enabled
        
        result = await self._request("GET", "/")
        if result:
            self._enabled = result.get("zapier_enabled", False) and result.get("zapier_connected", False)
        else:
            self._enabled = False
        return self._enabled
    
    async def get_tools(self) -> List[Dict]:
        """Get Zapier tools in OpenAI format"""
        if self._tools_cache is not None:
            return self._tools_cache
        
        if not await self.is_enabled():
            return []
        
        result = await self._request("GET", "/tools")
        if result:
            self._tools_cache = result.get("tools", [])
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
        self._enabled = None


# Singleton
zapier_bridge = ZapierBridge()
