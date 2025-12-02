"""System prompts for the LLM"""

ARTIFACT_RULES = """

ARTIFACT RULES:
- Use create_artifact() ONLY for the FIRST creation of visual content
- To MODIFY an existing artifact, use replace_in_artifact()
- NEVER use edit_artifact() - it's deprecated
- Each replace_in_artifact() creates a new version (V2, V3, etc.)

HOW TO MODIFY AN ARTIFACT:
1. get_artifact() to see current code
2. Find the EXACT string to change
3. replace_in_artifact(old_string="exact", new_string="new", description="change")"""


def build_system_prompt(tool_names: list, user_context: dict = None) -> dict:
    """Build system prompt that forces tool-only behavior"""
    
    rules = ARTIFACT_RULES if "create_artifact" in tool_names else ""
    
    # Build user context section if provided
    context_section = ""
    if user_context:
        ctx_lines = "\n".join(f"- {k}: {v}" for k, v in user_context.items())
        context_section = f"""

## USER CONTEXT (auto-injected, use these values for tools that need them)
{ctx_lines}
IMPORTANT: When a tool needs telegram_chat_id or similar, use the values above. Do NOT ask the user for these."""
    
    return {
        "role": "system",
        "content": f"""You MUST use tools for EVERYTHING. Available: {', '.join(tool_names)}.

RULES:
1. send_message() to communicate - NEVER plain text
2. think() for reasoning (shown separately to user)
3. NEVER repeat think() content in send_message()
4. Work step by step - one tool at a time
5. Call task_complete() when done{rules}{context_section}

Example: "Explain 2+2=4"
1. think("Let me reason...")
2. send_message("2+2=4 because...")
3. task_complete()"""
    }
