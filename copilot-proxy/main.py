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
    
    # AGENTIC LOOP - All actions are tool calls
    # Collect events in chronological order for proper display
    events = []  # List of {"type": "message"|"tool_call", "content": ...}
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
        
        # Make request
        result = await make_copilot_request(loop_body, copilot_token)
        
        if not result:
            print("Request failed, breaking loop")
            break
        
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")
        tool_calls = message.get("tool_calls", [])
        
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
                    events.append(event)
                    content = event.get("content", "")[:50]
                    print(f"  {tc_name}: {event.get('type')} - {content}...")
                    continue
            
            # Default: show as regular tool call
            events.append({
                "type": "tool_call",
                "tool_call": {"name": tc_name, "arguments": tc_args_str, "result": tc_result_str}
            })
            print(f"  {tc_name}: done")
        
        # Exit loop if task_complete was called
        if task_done:
            print("Task marked as complete, exiting agentic loop")
            break
        
        # Add assistant message and tool results to conversation
        current_messages.append(message)
        current_messages.extend(tool_results)
    
    # Count events for logging
    tool_count = sum(1 for e in events if e["type"] == "tool_call")
    msg_count = sum(1 for e in events if e["type"] == "message")
    print(f"\nAgentic loop complete. Iterations: {iteration}, Tool calls: {tool_count}, Messages: {msg_count}")
    
    if stream:
        async def stream_agentic():
            # Send events in chronological order
            for event in events:
                if event["type"] == "tool_call":
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_call': event['tool_call']})}\n\n"
                elif event["type"] == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']})}\n\n"
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
            stream_agentic(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        # Non-streaming: return result with events in order
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
            "events": events  # Include chronological events
        }
        if all_tool_calls:
            result["tool_calls_executed"] = all_tool_calls
        return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "healthy"}
