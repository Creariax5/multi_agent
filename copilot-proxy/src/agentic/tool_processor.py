"""Process tool calls and convert to events"""
import json
import logging
from src.mcp_client import execute_tool_calls, tool_to_event
from src.copilot import make_request

logger = logging.getLogger(__name__)


def parse_json(s: str) -> dict:
    """Safely parse JSON string"""
    try:
        return json.loads(s) if s else {}
    except:
        return {}


async def process_tools(tool_calls: list, tool_handlers: dict, copilot_token: str = None):
    """
    Execute tool calls and yield events.
    
    Yields: event dicts or special control events
    """
    if not tool_calls:
        return
    
    logger.info(f"⚡ Executing {len(tool_calls)} tool(s)...")
    results = await execute_tool_calls(tool_calls)
    
    for tc in tool_calls:
        name = tc["function"]["name"]
        args_str = tc["function"].get("arguments", "{}")
        tc_id = tc["id"]
        
        # Get result for this tool
        result_str = next((r["content"] for r in results if r["tool_call_id"] == tc_id), "{}")
        
        # Handle summarize specially
        if name == "summarize_conversation" and copilot_token:
            async for event in _handle_summarize(copilot_token):
                yield event
            continue
        
        handler = tool_handlers.get(name, {})
        
        # Terminal tool - signal to stop loop
        if handler.get("is_terminal"):
            logger.info(f"🏁 {name}: Terminal tool")
            yield {"type": "terminal", "name": name}
            continue
        
        # Convert to UI event via MCP
        if handler.get("has_to_event"):
            # Skip if already streamed
            if tc.get("streamed") and name in ("think", "send_message"):
                continue
            
            event = await tool_to_event(name, parse_json(args_str), parse_json(result_str))
            if event:
                logger.info(f"📤 {name} → {event.get('type')}")
                yield event
                continue
        
        # Default: generic tool_call event
        logger.info(f"✅ {name}: done")
        yield {"type": "tool_call", "tool_call": {"name": name, "arguments": args_str, "result": result_str}}


async def _handle_summarize(copilot_token: str):
    """Handle summarize_conversation by calling Copilot to generate summary"""
    logger.info("📝 Summarizing conversation...")
    # Note: This is a placeholder - actual implementation would need messages
    yield {"type": "thinking", "content": "Summarizing conversation..."}
