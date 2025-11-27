
def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "summarize_conversation",
            "description": "Summarize the current conversation history to save context space. Use this when the conversation is getting too long.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


def execute() -> dict:
    """
    Execute the tool. 
    NOTE: This is a special tool handled by the proxy. 
    The proxy will intercept this and perform the summarization.
    """
    return {"status": "handled_by_proxy"}


def to_event(args: dict, result: dict) -> dict:
    """
    Transform tool call into UI event.
    """
    return {
        "type": "thinking",
        "content": "Summarizing conversation history..."
    }


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
