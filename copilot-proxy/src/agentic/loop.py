"""Main agentic loop - orchestrates tool calling iterations"""
import logging
from src.config import MAX_AGENTIC_ITERATIONS, AUTO_SUMMARIZE_THRESHOLD
from src.prompts import build_system_prompt
from .copilot_stream import stream_copilot
from .realtime import extract_delta, get_event_type
from .tool_processor import process_tools

logger = logging.getLogger(__name__)


async def run_agentic_loop(messages: list, copilot_token: str, mcp_tools: list, 
                           tool_handlers: dict, use_tools: bool = True, model: str = "gpt-4.1"):
    """Run the agentic loop - yields events as they occur."""
    
    current_messages = _prepare_messages(messages, mcp_tools, use_tools)
    yield {"type": "model_info", "model": model}
    
    for iteration in range(1, MAX_AGENTIC_ITERATIONS + 1):
        logger.info(f"🔄 Iteration {iteration}/{MAX_AGENTIC_ITERATIONS}")
        
        # Build request
        body = {"model": model, "messages": current_messages, "stream": True}
        if mcp_tools and use_tools:
            body["tools"] = mcp_tools
            body["tool_choice"] = "required"
        
        # Stream and collect tool calls
        tool_buffer = {}
        async for chunk_type, data in stream_copilot(copilot_token, current_messages, body):
            if chunk_type == "error":
                logger.error(f"❌ Copilot error: {data}")
                return
            if chunk_type == "done":
                break
            if chunk_type == "tool_chunk":
                event = _process_chunk(tool_buffer, data)
                if event:
                    yield event
        
        # Reconstruct tool calls
        tool_calls = _build_tool_calls(tool_buffer)
        if not tool_calls:
            logger.info("No tool calls, exiting")
            break
        
        # Process tools
        task_done = False
        async for event in process_tools(tool_calls, tool_handlers, copilot_token):
            if event.get("type") == "terminal":
                task_done = True
            else:
                yield event
        
        if task_done:
            logger.info("🎉 Task complete")
            break
        
        # Update messages for next iteration
        current_messages.append({"role": "assistant", "tool_calls": tool_calls})
        # Note: tool results would be added here from process_tools
    
    logger.info(f"✨ Agentic loop complete")


def _prepare_messages(messages: list, mcp_tools: list, use_tools: bool) -> list:
    """Prepare messages with system prompt"""
    msgs = messages.copy()
    
    if mcp_tools and use_tools:
        tool_names = [t["function"]["name"] for t in mcp_tools]
        
        if not any(m.get("role") == "system" for m in msgs):
            msgs = [build_system_prompt(tool_names)] + msgs
        
        if len(msgs) > AUTO_SUMMARIZE_THRESHOLD:
            logger.warning(f"⚠️ Auto-summarize: {len(msgs)} messages")
            msgs.append({"role": "system", "content": "SYSTEM: Call summarize_conversation() NOW."})
    
    return msgs


def _process_chunk(buffer: dict, data: dict):
    """Process a tool call chunk, return event if any"""
    idx = data["index"]
    
    if idx not in buffer:
        buffer[idx] = {"id": "", "name": "", "arguments": "", "yielded_len": 0}
    
    if data["id"]:
        buffer[idx]["id"] = data["id"]
    if data["name"]:
        buffer[idx]["name"] = data["name"]
    if data["arguments"]:
        buffer[idx]["arguments"] += data["arguments"]
        
        # Check for real-time streaming
        name = buffer[idx]["name"]
        args = buffer[idx]["arguments"]
        content, new_len = extract_delta(name, args, buffer[idx]["yielded_len"])
        
        if content:
            buffer[idx]["yielded_len"] = new_len
            buffer[idx]["streamed"] = True
            event_type = get_event_type(name)
            return {"type": event_type, "content": content}
    
    return None


def _build_tool_calls(buffer: dict) -> list:
    """Build tool calls list from buffer"""
    return [
        {
            "id": data["id"],
            "type": "function", 
            "function": {"name": data["name"], "arguments": data["arguments"]},
            "streamed": data.get("streamed", False)
        }
        for data in (buffer[i] for i in sorted(buffer))
    ]
