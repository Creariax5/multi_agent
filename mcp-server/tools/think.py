"""
Think Tool - Allows the AI to reason step by step
Displays thinking in a special collapsible block in the UI
"""


def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "think",
            "description": "Use this tool to think through a problem step by step before answering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your reasoning process"
                    }
                },
                "required": ["thought"]
            }
        }
    }


def execute(thought: str) -> dict:
    """Execute the tool and return result"""
    return {"content": thought}


def to_event(args: dict, result: dict) -> dict:
    """
    Transform tool call into UI event.
    Returns None to use default tool_call display.
    """
    return {
        "type": "thinking",
        "content": args.get("thought", "")
    }


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
