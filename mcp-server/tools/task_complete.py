"""
Task Complete Tool - Signals that the task is finished
"""


def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": "Call this when you have completed ALL steps of the user's request.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


def execute() -> dict:
    """Execute the tool and return result"""
    return {"status": "complete"}


def to_event(args: dict, result: dict) -> dict:
    """No UI event for this tool"""
    return None


def is_terminal() -> bool:
    """This tool ends the agentic loop"""
    return True
