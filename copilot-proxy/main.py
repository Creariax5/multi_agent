"""
Simple Copilot Proxy - Exposes GitHub Copilot as OpenAI-compatible API
With MCP Tools support using GPT-4.1 (free) for tool calls
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
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8081")

# Model used for tool calls (FREE = no credits)
TOOL_CALL_MODEL = "gpt-4.1"

# Max iterations for agentic loop
MAX_AGENTIC_ITERATIONS = 15

# Auto-summarize threshold (number of messages)
AUTO_SUMMARIZE_THRESHOLD = 10

# Cache for the Copilot access token
cached_token = None
token_expires_at = 0

# Cache for MCP tools and metadata
cached_tools = None
cached_metas = None


def clean_messages(messages: list) -> list:
    """Clean messages to only include valid fields for API"""
    cleaned = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        # Only include valid roles
        if role not in ["system", "user", "assistant"]:
            continue
        
        # If assistant message had tool_calls, add info to content
        if role == "assistant" and msg.get("tool_calls"):
            tool_info = []
            for tc in msg.get("tool_calls", []):
                name = tc.get("name", "unknown")
                result = tc.get("result", "")
                tool_info.append(f"[Used tool {name}: {result}]")
            if tool_info:
                content = "\n".join(tool_info) + "\n" + content
        
        clean_msg = {"role": role, "content": content}
        cleaned.append(clean_msg)
    return cleaned


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


async def get_mcp_tools():
    """Fetch available tools from MCP server"""
    global cached_tools
    
    if cached_tools:
        return cached_tools
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/tools")
            if response.status_code == 200:
                data = response.json()
                cached_tools = data.get("tools", [])
                print(f"Loaded {len(cached_tools)} tools from MCP server")
                return cached_tools
    except Exception as e:
        print(f"Failed to fetch MCP tools: {e}")
    
    return []


async def get_tool_handlers():
    """Fetch tool handler info from MCP server"""
    global cached_metas
    
    if cached_metas is not None:
        return cached_metas
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MCP_SERVER_URL}/tools/handlers")
            if response.status_code == 200:
                data = response.json()
                cached_metas = data.get("handlers", {})
                return cached_metas
    except Exception as e:
        print(f"Failed to fetch handlers: {e}")
    
    return {}


async def tool_to_event(name: str, args: dict, result: dict) -> dict:
    """Ask MCP server to convert tool call to UI event"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/tools/to_event",
                json={"name": name, "arguments": args, "result": result}
            )
            if response.status_code == 200:
                return response.json().get("event")
    except:
        pass
    return None


async def execute_tool_calls(tool_calls: list) -> list:
    """Execute tool calls via MCP server"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/execute_batch",
                json={"tool_calls": tool_calls}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
    except Exception as e:
        print(f"Failed to execute tools: {e}")
        return [
            {
                "tool_call_id": tc.get("id", "unknown"),
                "role": "tool",
                "content": json.dumps({"error": str(e)})
            }
            for tc in tool_calls
        ]
    
    return []


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
            print(f"Copilot API error: {response.status_code} {response.text}")
            return None
        
        return response.json()


@app.get("/")
async def root():
    return {"status": "ok", "message": "Copilot Proxy with MCP Tools is running"}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4.1", "object": "model", "owned_by": "github-copilot", "cost": "FREE"},
            {"id": "gpt-4o", "object": "model", "owned_by": "github-copilot", "cost": "FREE"},
            {"id": "gpt-4", "object": "model", "owned_by": "github-copilot"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "github-copilot"},
            {"id": "claude-sonnet-4", "object": "model", "owned_by": "github-copilot", "cost": "1 credit"},
            {"id": "claude-opus-4.5", "object": "model", "owned_by": "github-copilot", "cost": "1 credit"},
        ]
    }


@app.get("/v1/tools")
async def list_tools():
    """Get available MCP tools"""
    tools = await get_mcp_tools()
    return {"tools": tools, "count": len(tools)}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Chat completions with AGENTIC tool handling - loop until done"""
    print("=" * 60)
    print("Received chat completion request (AGENTIC MODE)")
    
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Clean messages to remove any tool_calls or invalid fields
    body["messages"] = clean_messages(body.get("messages", []))
    
    copilot_token = await get_copilot_token()
    
    original_model = body.get("model", "gpt-4.1")
    use_tools = body.get("use_tools", True)
    stream = body.get("stream", False)
    
    print(f"Model: {original_model}, Use Tools: {use_tools}, Stream: {stream}")
    
    # Get MCP tools and handlers
    mcp_tools = []
    tool_handlers = {}
    if use_tools:
        mcp_tools = await get_mcp_tools()
        tool_handlers = await get_tool_handlers()
        if mcp_tools:
            print(f"Loaded {len(mcp_tools)} MCP tools")
            
            # System message forcing tool-only behavior
            tool_names = [t["function"]["name"] for t in mcp_tools]
            system_msg = {
                "role": "system",
                "content": f"""You MUST use tools for EVERYTHING. Available tools: {', '.join(tool_names)}.

CRITICAL RULES:
1. Use send_message() to communicate with the user - NEVER respond with plain text
2. Use think() for complex reasoning - the thought content is shown separately to the user
3. NEVER repeat the content of think() in send_message() - keep them independent
4. Use other tools (calculate, get_weather, etc.) for actions  
5. Work step by step - one tool call at a time
6. When you have completed ALL tasks, call task_complete() to finish

Example for "Explain why 2+2=4":
1. think("Let me reason about this mathematically...")
2. send_message("2+2=4 because addition combines quantities.")
3. task_complete()

IMPORTANT: think() shows your reasoning process, send_message() shows the final answer - DO NOT duplicate content between them!"""
            }
            messages = body.get("messages", [])
            if not any(m.get("role") == "system" for m in messages):
                body["messages"] = [system_msg] + messages
            
            # Auto-summarize check
            current_msg_count = len(body["messages"])
            if current_msg_count > AUTO_SUMMARIZE_THRESHOLD:
                 print(f"Auto-summarize triggered: {current_msg_count} messages")
                 body["messages"].append({
                    "role": "system",
                    "content": "SYSTEM NOTICE: The conversation history is very long. You MUST call summarize_conversation() NOW to compress it before proceeding with the user's request."
                 })
    
    # Core agentic loop generator
    async def agentic_loop():
        current_messages = body.get("messages", []).copy()
        iteration = 0
        
        while iteration < MAX_AGENTIC_ITERATIONS:
            iteration += 1
            print(f"\n--- Agentic iteration {iteration} ---")
            
            # Build request with tools - force tool use
            loop_body = {
                "model": TOOL_CALL_MODEL,
                "messages": current_messages,
                "stream": False
            }
            
            if mcp_tools and use_tools:
                loop_body["tools"] = mcp_tools
                loop_body["tool_choice"] = "required"  # Force tool use
            
            # Build request with tools - force tool use
            loop_body = {
                "model": TOOL_CALL_MODEL,
                "messages": current_messages,
                "stream": True  # Always stream from Copilot to support real-time tool args
            }
            
            if mcp_tools and use_tools:
                loop_body["tools"] = mcp_tools
                loop_body["tool_choice"] = "required"  # Force tool use
            
            # Make request
            print("Sending streaming request to Copilot...")
            
            # We need to handle the stream manually here
            is_tool_continuation = any(
                msg.get("role") == "tool" for msg in current_messages
            )
            initiator = "agent" if is_tool_continuation else "user"
            
            headers = {
                "Authorization": f"Bearer {copilot_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Editor-Version": "vscode/1.103.2",
                "Copilot-Integration-Id": "vscode-chat",
                "X-Initiator": initiator,
                "x-github-api-version": "2025-05-01",
                "User-Agent": "GitHubCopilotChat/0.12.0",
            }

            tool_calls_buffer = {}  # id -> {name, args_buffer}
            finish_reason = None
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{COPILOT_API_URL}/chat/completions", headers=headers, json=loop_body) as response:
                    if response.status_code != 200:
                        print(f"Copilot API error: {response.status_code}")
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
                            
                            # Handle tool calls in delta
                            if "tool_calls" in delta:
                                for tc_chunk in delta["tool_calls"]:
                                    idx = tc_chunk.get("index")
                                    tc_id = tc_chunk.get("id")
                                    tc_fn = tc_chunk.get("function", {})
                                    tc_name = tc_fn.get("name")
                                    tc_args = tc_fn.get("arguments", "")
                                    
                                    if idx not in tool_calls_buffer:
                                        tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}
                                    
                                    if tc_id:
                                        tool_calls_buffer[idx]["id"] = tc_id
                                    if tc_name:
                                        tool_calls_buffer[idx]["name"] = tc_name
                                    if tc_args:
                                        tool_calls_buffer[idx]["arguments"] += tc_args
                                        
                                        # STREAMING LOGIC:
                                        current_tool_name = tool_calls_buffer[idx]["name"]
                                        current_args = tool_calls_buffer[idx]["arguments"]
                                        
                                        # Initialize yielded_len if not present
                                        if "yielded_len" not in tool_calls_buffer[idx]:
                                            tool_calls_buffer[idx]["yielded_len"] = 0
                                            
                                        # Handle think() - strip JSON wrapper {"thought": "..."}
                                        if current_tool_name == "think":
                                            prefix = '{"thought": "'
                                            if current_args.startswith(prefix):
                                                start_idx = max(len(prefix), tool_calls_buffer[idx]["yielded_len"])
                                                new_content = current_args[start_idx:]
                                                if new_content:
                                                    yield {
                                                        "type": "thinking_delta",
                                                        "content": new_content
                                                    }
                                                    tool_calls_buffer[idx]["yielded_len"] += len(new_content)

                                        # Handle send_message() - strip JSON wrapper {"message": "..."}
                                        elif current_tool_name == "send_message":
                                            prefix = '{"message": "'
                                            if current_args.startswith(prefix):
                                                start_idx = max(len(prefix), tool_calls_buffer[idx]["yielded_len"])
                                                new_content = current_args[start_idx:]
                                                if new_content:
                                                    yield {
                                                        "type": "message_delta",
                                                        "content": new_content
                                                    }
                                                    tool_calls_buffer[idx]["yielded_len"] += len(new_content)
                                                    tool_calls_buffer[idx]["streamed"] = True

                        except Exception as e:
                            print(f"Error parsing chunk: {e}")

            # Reconstruct full tool calls list
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
            
            # Reconstruct the full message object for history
            message = {
                "role": "assistant",
                "tool_calls": tool_calls
            }
            
            print(f"Finish reason: {finish_reason}, Tool calls: {len(tool_calls)}")
            
            # If no tool calls, we're done (shouldn't happen with tool_choice=required)
            if not tool_calls:
                print("No tool calls, exiting loop")
                break
            
            # Execute tool calls
            print(f"Executing {len(tool_calls)} tool calls...")
            tool_results = await execute_tool_calls(tool_calls)
            
            # Process each tool call - delegate to MCP server
            task_done = False
            for tc in tool_calls:
                tc_name = tc.get("function", {}).get("name")
                tc_args_str = tc.get("function", {}).get("arguments", "{}")
                
                # SPECIAL HANDLING: summarize_conversation
                if tc_name == "summarize_conversation":
                    print("  summarize_conversation: Intercepted by proxy")
                    
                    # Generate summary using LLM
                    summary_prompt = [
                        {"role": "system", "content": "You are a helpful assistant. Summarize the following conversation concisely to save context space. Preserve key information and user intent."},
                        {"role": "user", "content": json.dumps(current_messages)}
                    ]
                    
                    try:
                        summary_response = await make_copilot_request({
                            "model": "gpt-3.5-turbo",
                            "messages": summary_prompt
                        }, copilot_token)
                        
                        summary_text = summary_response["choices"][0]["message"]["content"]
                        print(f"  Summary generated: {summary_text[:50]}...")
                        
                        # Emit summary event
                        yield {
                            "type": "thinking",
                            "content": f"**Conversation Summarized:**\n{summary_text}"
                        }
                        
                        # Update current context with summary
                        # We keep the system prompt and replace the rest with the summary
                        system_prompts = [m for m in current_messages if m.get("role") == "system"]
                        new_history = system_prompts + [
                            {"role": "user", "content": f"Here is a summary of the previous conversation:\n{summary_text}\n\nContinue from here."}
                        ]
                        current_messages = new_history
                        
                        # Emit history update event so frontend can sync
                        yield {
                            "type": "history_update",
                            "messages": new_history
                        }
                        
                        # Mark this tool as handled (no need to call MCP)
                        continue
                        
                    except Exception as e:
                        print(f"  Summary generation failed: {e}")
                        yield {"type": "thinking", "content": f"Failed to summarize conversation: {e}"}

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
                
                # Get handler info
                handler = tool_handlers.get(tc_name, {})
                
                # Check if terminal tool
                if handler.get("is_terminal"):
                    print(f"  {tc_name}: Terminal - ending loop")
                    task_done = True
                    continue
                
                # Ask MCP server to convert to UI event
                if handler.get("has_to_event"):
                    event = await tool_to_event(tc_name, tc_args, tc_result)
                    if event:
                        # Special case: send_message
                        if tc_name == "send_message" and tc.get("streamed", False):
                            print(f"  {tc_name}: Already streamed, skipping final event")
                            continue

                        content = event.get("content", "")[:50]
                        print(f"  {tc_name}: {event.get('type')} - {content}...")
                        yield event
                        continue
                
                # Default: show as regular tool call
                print(f"  {tc_name}: done")
                yield {
                    "type": "tool_call",
                    "tool_call": {"name": tc_name, "arguments": tc_args_str, "result": tc_result_str}
                }
            
            # Exit loop if task_complete was called
            if task_done:
                print("Task marked as complete, exiting agentic loop")
                break
            
            # Add assistant message and tool results to conversation
            current_messages.append(message)
            current_messages.extend(tool_results)
        
        print(f"\nAgentic loop complete. Iterations: {iteration}")

    if stream:
        async def stream_response():
            async for event in agentic_loop():
                if event["type"] == "tool_call":
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_call': event['tool_call']})}\n\n"
                elif event["type"] == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']})}\n\n"
                elif event["type"] == "thinking_delta":
                    yield f"data: {json.dumps({'type': 'thinking_delta', 'content': event['content']})}\n\n"
                elif event["type"] == "message_delta":
                    chunk = {
                        "id": "agentic",
                        "object": "chat.completion.chunk",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": event["content"]},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif event["type"] == "history_update":
                    yield f"data: {json.dumps({'type': 'history_update', 'messages': event['messages']})}\n\n"
                elif event["type"] == "message":
                    chunk = {
                        "id": "agentic",
                        "object": "chat.completion.chunk",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": event["content"]},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            # Send done signal
            done_chunk = {
                "id": "agentic",
                "object": "chat.completion.chunk", 
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        # Non-streaming: collect all events
        events = []
        async for event in agentic_loop():
            events.append(event)
            
        all_messages = [e["content"] for e in events if e["type"] == "message"]
        all_tool_calls = [e["tool_call"] for e in events if e["type"] == "tool_call"]
        final_content = "\n\n".join(all_messages)
        
        result = {
            "id": "agentic",
            "object": "chat.completion",
            "model": original_model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_content
                },
                "finish_reason": "stop"
            }],
            "events": events
        }
        if all_tool_calls:
            result["tool_calls_executed"] = all_tool_calls
        return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "healthy"}
