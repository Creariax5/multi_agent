"""
Message utilities and helpers
"""


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


def build_system_prompt(tool_names: list) -> dict:
    """Build the system message that forces tool-only behavior"""
    
    has_artifacts = 'create_artifact' in tool_names
    has_replace = 'replace_in_artifact' in tool_names
    
    artifact_rules = ""
    if has_artifacts:
        artifact_rules = """

ARTIFACT RULES:
- Use create_artifact() ONLY for the FIRST creation of visual content (HTML pages, dashboards, games, etc.)
- To MODIFY an existing artifact, use replace_in_artifact() - it's simple and reliable like find-and-replace
- NEVER use edit_artifact() - it's deprecated and breaks code easily
- NEVER create a new artifact just to show updated code - use replace_in_artifact() instead
- Each replace_in_artifact() creates a new version (V2, V3, etc.)

HOW TO MODIFY AN ARTIFACT:
1. Use get_artifact() to see the current code
2. Find the EXACT string you want to change
3. Use replace_in_artifact(old_string="exact text", new_string="new text", description="what changed")

Example - change game speed:
  replace_in_artifact(old_string="let speed = 100;", new_string="let speed = 300;", description="Slow down 3x")

This is MUCH more reliable than DOM manipulation!"""
    
    return {
        "role": "system",
        "content": f"""You MUST use tools for EVERYTHING. Available tools: {', '.join(tool_names)}.

CRITICAL RULES:
1. Use send_message() to communicate with the user - NEVER respond with plain text
2. Use think() for complex reasoning - the thought content is shown separately to the user
3. NEVER repeat the content of think() in send_message() - keep them independent
4. Use other tools (calculate, get_weather, etc.) for actions  
5. Work step by step - one tool call at a time
6. When you have completed ALL tasks, call task_complete() to finish{artifact_rules}

Example for "Explain why 2+2=4":
1. think("Let me reason about this mathematically...")
2. send_message("2+2=4 because addition combines quantities.")
3. task_complete()

IMPORTANT: think() shows your reasoning process, send_message() shows the final answer - DO NOT duplicate content between them!"""
    }
