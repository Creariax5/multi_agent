"""
Send Message Tool - Send text messages to the user
"""


def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a text message to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send"
                    }
                },
                "required": ["message"]
            }
        }
    }


def execute(message: str) -> dict:
    """Execute the tool and return result"""
    return {"content": message}


def to_event(args: dict, result: dict) -> dict:
    """Transform tool call into UI event"""
    return {
        "type": "message",
        "content": args.get("message", "")
    }


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
