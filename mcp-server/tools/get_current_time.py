"""Tool: get_current_time - Get current date and time"""
from datetime import datetime, timezone as tz


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["iso", "human", "unix"], "default": "human"}
                },
                "required": []
            }
        }
    }


def execute(format: str = "human") -> dict:
    """Get current time"""
    now = datetime.now(tz.utc)
    
    formats = {
        "iso": {"time": now.isoformat()},
        "unix": {"timestamp": int(now.timestamp())},
        "human": {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"), "day": now.strftime("%A")}
    }
    return formats.get(format, formats["human"])
