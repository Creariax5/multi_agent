"""
Agentic loop - Core logic for multi-turn tool calling
"""
import json
import logging
import httpx

from src.config import (
    COPILOT_API_URL, 
    TOOL_CALL_MODEL, 
    MAX_AGENTIC_ITERATIONS,
    AUTO_SUMMARIZE_THRESHOLD
)
from src.auth import get_copilot_headers, make_copilot_request
from src.mcp_client import execute_tool_calls, tool_to_event
from src.messages import build_system_prompt

logger = logging.getLogger(__name__)


async def run_agentic_loop(
    messages: list,
    copilot_token: str,
    mcp_tools: list,
    tool_handlers: dict,
    use_tools: bool = True,
    model: str = "gpt-4.1"
):
    """
    Run the agentic loop - yields events as they occur.
    
    Args:
        messages: Initial conversation messages
        copilot_token: Copilot API token
        mcp_tools: List of available MCP tools
        tool_handlers: Dict of tool handler metadata
        use_tools: Whether to use tools
        model: The model to use for completions
        
    Yields:
        Events dict with type and content
    """
    current_messages = messages.copy()
    
    # Emit model info event
    yield {"type": "model_info", "model": model}
    
    # Add system prompt if tools are available
    if mcp_tools and use_tools:
        tool_names = [t["function"]["name"] for t in mcp_tools]
        system_msg = build_system_prompt(tool_names)
        
        if not any(m.get("role") == "system" for m in current_messages):
            current_messages = [system_msg] + current_messages
        
        # Auto-summarize check
        if len(current_messages) > AUTO_SUMMARIZE_THRESHOLD:
            logger.warning(f"⚠️ Auto-summarize triggered: {len(current_messages)} messages")
            current_messages.append({
                "role": "system",
                "content": "SYSTEM NOTICE: The conversation history is very long. You MUST call summarize_conversation() NOW to compress it before proceeding with the user's request."
            })
    
    iteration = 0
    
    while iteration < MAX_AGENTIC_ITERATIONS:
        iteration += 1
        logger.info(f"🔄 Iteration {iteration}/{MAX_AGENTIC_ITERATIONS}")
        
        # Build request body - use the selected model
        loop_body = {
            "model": model,
            "messages": current_messages,
            "stream": True
        }
        
        if mcp_tools and use_tools:
            loop_body["tools"] = mcp_tools
            loop_body["tool_choice"] = "required"
        
        # Stream from Copilot
        logger.debug("Sending streaming request to Copilot...")
        headers = get_copilot_headers(copilot_token, current_messages)
        
        tool_calls_buffer = {}
        finish_reason = None
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", 
                f"{COPILOT_API_URL}/chat/completions", 
                headers=headers, 
                json=loop_body
            ) as response:
                if response.status_code != 200:
                    logger.error(f"❌ Copilot API error: {response.status_code}")
                    break
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")
                        
                        # Handle streaming tool calls
                        if "tool_calls" in delta:
                            for tc_chunk in delta["tool_calls"]:
                                idx = tc_chunk.get("index")
                                
                                if idx not in tool_calls_buffer:
                                    tool_calls_buffer[idx] = {
                                        "id": "", 
                                        "name": "", 
                                        "arguments": "",
                                        "yielded_len": 0
                                    }
                                
                                tc_id = tc_chunk.get("id")
                                tc_fn = tc_chunk.get("function", {})
                                tc_name = tc_fn.get("name")
                                tc_args = tc_fn.get("arguments", "")
                                
                                if tc_id:
                                    tool_calls_buffer[idx]["id"] = tc_id
                                if tc_name:
                                    tool_calls_buffer[idx]["name"] = tc_name
                                if tc_args:
                                    tool_calls_buffer[idx]["arguments"] += tc_args
                                    
                                    # Stream think() and send_message() in real-time
                                    current_name = tool_calls_buffer[idx]["name"]
                                    current_args = tool_calls_buffer[idx]["arguments"]
                                    
                                    if current_name == "think":
                                        prefix = '{"thought": "'
                                        if current_args.startswith(prefix):
                                            start = max(len(prefix), tool_calls_buffer[idx]["yielded_len"])
                                            new_content = current_args[start:]
                                            # Remove trailing incomplete JSON
                                            if new_content.endswith('"}'):
                                                new_content = new_content[:-2]
                                            elif new_content.endswith('"'):
                                                new_content = new_content[:-1]
                                            if new_content:
                                                yield {"type": "thinking_delta", "content": new_content}
                                                tool_calls_buffer[idx]["yielded_len"] = len(current_args)
                                                tool_calls_buffer[idx]["streamed"] = True
                                    
                                    elif current_name == "send_message":
                                        prefix = '{"message": "'
                                        if current_args.startswith(prefix):
                                            start = max(len(prefix), tool_calls_buffer[idx]["yielded_len"])
                                            new_content = current_args[start:]
                                            # Remove trailing incomplete JSON (closing quote/brace)
                                            if new_content.endswith('"}'):
                                                new_content = new_content[:-2]
                                            elif new_content.endswith('"'):
                                                new_content = new_content[:-1]
                                            if new_content:
                                                yield {"type": "message_delta", "content": new_content}
                                                tool_calls_buffer[idx]["yielded_len"] = len(current_args)
                                                tool_calls_buffer[idx]["streamed"] = True
                    
                    except Exception as e:
                        logger.warning(f"Error parsing chunk: {e}")
        
        # Reconstruct tool calls
        tool_calls = []
        for idx in sorted(tool_calls_buffer.keys()):
            tc_data = tool_calls_buffer[idx]
            tool_calls.append({
                "id": tc_data["id"],
                "type": "function",
                "function": {
                    "name": tc_data["name"],
                    "arguments": tc_data["arguments"]
                },
                "streamed": tc_data.get("streamed", False)
            })
        
        message = {"role": "assistant", "tool_calls": tool_calls}
        logger.debug(f"Finish: {finish_reason} | Tool calls: {len(tool_calls)}")
        
        if not tool_calls:
            logger.info("No tool calls, exiting loop")
            break
        
        # Execute tools
        logger.info(f"⚡ Executing {len(tool_calls)} tool(s)...")
        tool_results = await execute_tool_calls(tool_calls)
        
        # Process each tool call
        task_done = False
        for tc in tool_calls:
            tc_name = tc.get("function", {}).get("name")
            tc_args_str = tc.get("function", {}).get("arguments", "{}")
            
            # Handle summarize_conversation specially
            if tc_name == "summarize_conversation":
                async for event in handle_summarize(current_messages, copilot_token):
                    if event.get("type") == "history_update":
                        current_messages = event["messages"]
                    yield event
                continue
            
            # Get result for this tool
            tc_result_str = next(
                (tr["content"] for tr in tool_results if tr["tool_call_id"] == tc["id"]),
                "{}"
            )
            
            # Parse args and result
            try:
                tc_args = json.loads(tc_args_str) if tc_args_str else {}
            except:
                tc_args = {}
            try:
                tc_result = json.loads(tc_result_str) if tc_result_str else {}
            except:
                tc_result = {}
            
            handler = tool_handlers.get(tc_name, {})
            
            # Check terminal
            if handler.get("is_terminal"):
                logger.info(f"🏁 {tc_name}: Terminal tool - ending loop")
                task_done = True
                continue
            
            # Convert to UI event via MCP
            if handler.get("has_to_event"):
                event = await tool_to_event(tc_name, tc_args, tc_result)
                if event:
                    if tc_name == "send_message" and tc.get("streamed", False):
                        logger.debug(f"{tc_name}: Already streamed, skipping")
                        continue
                    
                    logger.info(f"📤 {tc_name} → {event.get('type')}")
                    yield event
                    continue
            
            # Default event
            logger.info(f"✅ {tc_name}: done")
            yield {
                "type": "tool_call",
                "tool_call": {
                    "name": tc_name,
                    "arguments": tc_args_str,
                    "result": tc_result_str
                }
            }
        
        if task_done:
            logger.info("🎉 Task complete, exiting agentic loop")
            break
        
        current_messages.append(message)
        current_messages.extend(tool_results)
    
    logger.info(f"✨ Agentic loop complete ({iteration} iterations)")


async def handle_summarize(messages: list, copilot_token: str):
    """Handle summarize_conversation tool call"""
    logger.info("📝 summarize_conversation: Intercepted by proxy")
    
    summary_prompt = [
        {
            "role": "system", 
            "content": "You are a helpful assistant. Summarize the following conversation concisely to save context space. Preserve key information and user intent."
        },
        {"role": "user", "content": json.dumps(messages)}
    ]
    
    try:
        summary_response = await make_copilot_request({
            "model": "gpt-3.5-turbo",
            "messages": summary_prompt
        }, copilot_token)
        
        summary_text = summary_response["choices"][0]["message"]["content"]
        logger.info(f"📝 Summary generated ({len(summary_text)} chars)")
        
        yield {
            "type": "thinking",
            "content": f"**Conversation Summarized:**\n{summary_text}"
        }
        
        # Keep system prompts, replace rest with summary
        system_prompts = [m for m in messages if m.get("role") == "system"]
        new_history = system_prompts + [
            {"role": "user", "content": f"Here is a summary of the previous conversation:\n{summary_text}\n\nContinue from here."}
        ]
        
        yield {"type": "history_update", "messages": new_history}
        
    except Exception as e:
        logger.error(f"❌ Summary generation failed: {e}")
        yield {"type": "thinking", "content": f"Failed to summarize conversation: {e}"}
