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

# Cache for the Copilot access token
cached_token = None
token_expires_at = 0

# Cache for MCP tools
cached_tools = None


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
    """Chat completions with automatic tool handling using GPT-4.1 (free)"""
    print("=" * 60)
    print("Received chat completion request")
    
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
    
    # If tools are requested, add MCP tools
    if use_tools and "tools" not in body:
        mcp_tools = await get_mcp_tools()
        if mcp_tools:
            body["tools"] = mcp_tools
            body["tool_choice"] = "auto"
            print(f"Added {len(mcp_tools)} MCP tools to request")
            
            # Add system message to inform the model about available tools
            tool_names = [t["function"]["name"] for t in mcp_tools]
            system_msg = {
                "role": "system",
                "content": f"You have access to the following tools: {', '.join(tool_names)}. Use them when appropriate to help the user. For example, use 'get_weather' for weather questions, 'calculate' for math, 'get_current_time' for time, 'convert_units' for unit conversions, 'search_web' for web searches, 'generate_random' for random numbers."
            }
            # Insert system message at the beginning
            messages = body.get("messages", [])
            if not any(m.get("role") == "system" for m in messages):
                body["messages"] = [system_msg] + messages
    
    # For tool-enabled requests, use GPT-4.1 (free) for orchestration
    if use_tools and body.get("tools"):
        # Step 1: Check for tool calls with GPT-4.1 (FREE)
        tool_check_body = body.copy()
        tool_check_body["model"] = TOOL_CALL_MODEL
        tool_check_body["stream"] = False
        
        print(f"Step 1: Checking for tool calls with {TOOL_CALL_MODEL} (FREE)")
        result = await make_copilot_request(tool_check_body, copilot_token)
        
        if not result:
            # Fallback: try without tools
            print("Tool check failed, falling back to direct request")
            clean_body = body.copy()
            for key in ["tools", "tool_choice", "use_tools"]:
                clean_body.pop(key, None)
            
            if stream:
                async def stream_fallback():
                    headers = {
                        "Authorization": f"Bearer {copilot_token}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                        "Editor-Version": "vscode/1.103.2",
                        "Copilot-Integration-Id": "vscode-chat",
                        "X-Initiator": "user",
                        "x-github-api-version": "2025-05-01",
                        "User-Agent": "GitHubCopilotChat/0.12.0",
                    }
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream(
                            "POST",
                            f"{COPILOT_API_URL}/chat/completions",
                            headers=headers,
                            json=clean_body
                        ) as response:
                            async for line in response.aiter_lines():
                                if line:
                                    yield f"{line}\n"
                
                return StreamingResponse(
                    stream_fallback(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            return JSONResponse(status_code=500, content={"error": "Failed to get response"})
        
        # Check if the model wants to use tools
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        if tool_calls:
            print(f"Step 2: Model requested {len(tool_calls)} tool calls")
            
            # Execute the tool calls
            tool_results = await execute_tool_calls(tool_calls)
            print(f"Step 3: Executed tools, got {len(tool_results)} results")
            
            # Build messages with tool results
            messages = body.get("messages", []).copy()
            messages.append(message)
            messages.extend(tool_results)
            
            # Step 4: Final response with original model (or GPT-4.1 to save credits)
            final_body = {
                "model": original_model,
                "messages": messages,
                "stream": stream
            }
            
            print(f"Step 4: Generating final response with {original_model}")
            
            if stream:
                async def stream_with_tools():
                    # Send tool info first
                    tool_info = {
                        "type": "tool_calls",
                        "tool_calls": [
                            {
                                "name": tc.get("function", {}).get("name"),
                                "arguments": tc.get("function", {}).get("arguments"),
                                "result": next(
                                    (tr["content"] for tr in tool_results if tr["tool_call_id"] == tc["id"]),
                                    None
                                )
                            }
                            for tc in tool_calls
                        ]
                    }
                    yield f"data: {json.dumps(tool_info)}\n\n"
                    
                    # Stream the response
                    headers = {
                        "Authorization": f"Bearer {copilot_token}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                        "Editor-Version": "vscode/1.103.2",
                        "Copilot-Integration-Id": "vscode-chat",
                        "X-Initiator": "agent",
                        "x-github-api-version": "2025-05-01",
                        "User-Agent": "GitHubCopilotChat/0.12.0",
                    }
                    
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream(
                            "POST",
                            f"{COPILOT_API_URL}/chat/completions",
                            headers=headers,
                            json=final_body
                        ) as response:
                            async for line in response.aiter_lines():
                                if line:
                                    yield f"{line}\n"
                
                return StreamingResponse(
                    stream_with_tools(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                final_result = await make_copilot_request(final_body, copilot_token)
                if final_result:
                    final_result["tool_calls_executed"] = [
                        {
                            "name": tc.get("function", {}).get("name"),
                            "arguments": tc.get("function", {}).get("arguments"),
                            "result": next(
                                (tr["content"] for tr in tool_results if tr["tool_call_id"] == tc["id"]),
                                None
                            )
                        }
                        for tc in tool_calls
                    ]
                    return JSONResponse(content=final_result)
        else:
            # No tool calls needed - stream the response from GPT-4.1 result
            print("No tool calls needed, streaming response")
            content = message.get("content", "")
            
            if stream:
                async def stream_no_tools():
                    # Convert the non-streaming result to SSE format
                    # Send content in chunks to simulate streaming
                    chunk_size = 20
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i+chunk_size]
                        data = {
                            "choices": [{
                                "delta": {"content": chunk},
                                "index": 0
                            }]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"
                
                return StreamingResponse(
                    stream_no_tools(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                return JSONResponse(content=result)
    
    # Direct request (no tools or model already checked)
    is_tool_continuation = any(msg.get("role") == "tool" for msg in body.get("messages", []))
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
    
    # Remove tools for direct request
    clean_body = body.copy()
    if "tools" in clean_body:
        del clean_body["tools"]
    if "tool_choice" in clean_body:
        del clean_body["tool_choice"]
    if "use_tools" in clean_body:
        del clean_body["use_tools"]
    
    if stream:
        async def stream_response():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{COPILOT_API_URL}/chat/completions",
                    headers=headers,
                    json=clean_body
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"data: {json.dumps({'error': str(error_text)})}\n\n"
                        return
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n"
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    # Non-streaming
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{COPILOT_API_URL}/chat/completions",
            headers=headers,
            json=clean_body
        )
        
        if response.status_code != 200:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})
        
        return JSONResponse(content=response.json())


@app.get("/health")
async def health():
    return {"status": "healthy"}
