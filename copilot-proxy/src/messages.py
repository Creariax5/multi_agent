"""Message cleaning utilities"""


def clean_messages(messages: list) -> list:
    """Clean messages for API - only valid roles and content"""
    cleaned = []
    
    for msg in messages:
        role = msg.get("role")
        if role not in ("system", "user", "assistant"):
            continue
        
        content = msg.get("content", "")
        
        # Add tool info to assistant messages that had tool_calls
        if role == "assistant" and msg.get("tool_calls"):
            tool_info = [f"[Used {tc.get('name', '?')}: {tc.get('result', '')}]" for tc in msg["tool_calls"]]
            content = "\n".join(tool_info) + "\n" + content
        
        cleaned.append({"role": role, "content": content})
    
    return cleaned
