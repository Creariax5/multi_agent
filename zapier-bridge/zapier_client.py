"""
Zapier MCP Client - Connects to Zapier MCP server via FastMCP StreamableHttpTransport

Zapier MCP uses the standard MCP protocol over HTTP.
See: https://docs.zapier.com/mcp/home
"""
import json
import logging
from typing import Optional, Dict, Any, List

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from config import ZAPIER_MCP_URL, ZAPIER_ENABLED

logger = logging.getLogger(__name__)


class ZapierMCPClient:
    """Client for Zapier MCP Server using FastMCP StreamableHttpTransport"""
    
    def __init__(self):
        self.url = ZAPIER_MCP_URL
        self.enabled = ZAPIER_ENABLED
        self._tools_cache: Optional[List[Dict]] = None
        self._client: Optional[Client] = None
        self._connected = False
    
    async def _ensure_connected(self) -> bool:
        """Ensure client is connected"""
        if not self.enabled:
            return False
        
        if self._connected and self._client:
            return True
        
        try:
            transport = StreamableHttpTransport(self.url)
            self._client = Client(transport=transport)
            await self._client.__aenter__()
            self._connected = True
            logger.info(f"✅ Connected to Zapier MCP")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Zapier MCP: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Zapier MCP"""
        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
            except:
                pass
            self._connected = False
            self._client = None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from Zapier MCP"""
        if self._tools_cache is not None:
            return self._tools_cache
        
        if not await self._ensure_connected():
            return []
        
        try:
            tools = await self._client.list_tools()
            self._tools_cache = []
            
            for tool in tools:
                self._tools_cache.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {"type": "object", "properties": {}}
                })
            
            logger.info(f"📦 Loaded {len(self._tools_cache)} tools from Zapier MCP")
            return self._tools_cache
        except Exception as e:
            logger.error(f"Error listing Zapier tools: {e}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Zapier MCP tool"""
        if not await self._ensure_connected():
            return {"success": False, "error": "Not connected to Zapier MCP"}
        
        try:
            # Add instructions parameter as Zapier expects it
            if "instructions" not in arguments:
                arguments["instructions"] = f"Execute the {name} tool with the provided parameters"
            
            result = await self._client.call_tool(name, arguments)
            
            # Parse result
            if result.content and len(result.content) > 0:
                text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                try:
                    return {"success": True, "result": json.loads(text)}
                except json.JSONDecodeError:
                    return {"success": True, "result": text}
            
            return {"success": True, "result": "Tool executed successfully"}
        except Exception as e:
            logger.error(f"Error calling Zapier tool {name}: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_cache(self):
        """Clear tools cache"""
        self._tools_cache = None
    
    def get_tools_as_openai_format(self, tools: List[Dict]) -> List[Dict]:
        """Convert MCP tools to OpenAI function format for copilot"""
        openai_tools = []
        for tool in tools:
            # Add zapier_ prefix to distinguish from local tools
            openai_tool = {
                "type": "function",
                "function": {
                    "name": f"zapier_{tool['name']}",
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools


# Singleton instance
zapier_client = ZapierMCPClient()
