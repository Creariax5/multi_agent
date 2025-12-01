"""Real-time streaming for think() and send_message()"""
from typing import Optional, Tuple

# Tools that support real-time streaming with their JSON prefix
STREAMABLE_TOOLS = {
    "think": ('{"thought": "', "thinking_delta"),
    "send_message": ('{"message": "', "message_delta"),
}


def extract_delta(tool_name: str, args: str, yielded_len: int) -> Tuple[str, int]:
    """
    Extract new content from streaming tool arguments.
    
    Returns: (new_content, new_yielded_len)
    """
    if tool_name not in STREAMABLE_TOOLS:
        return "", yielded_len
    
    prefix, _ = STREAMABLE_TOOLS[tool_name]
    
    if not args.startswith(prefix):
        return "", yielded_len
    
    start = max(len(prefix), yielded_len)
    new_content = args[start:]
    
    # Remove trailing incomplete JSON
    for suffix in ['"}', '"']:
        if new_content.endswith(suffix):
            new_content = new_content[:-len(suffix)]
            break
    
    return new_content, len(args) if new_content else yielded_len


def get_event_type(tool_name: str) -> Optional[str]:
    """Get the event type for a streamable tool"""
    if tool_name in STREAMABLE_TOOLS:
        return STREAMABLE_TOOLS[tool_name][1]
    return None
