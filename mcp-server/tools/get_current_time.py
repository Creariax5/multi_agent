"""
Tool: get_current_time - Get current date and time
"""
from datetime import datetime


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "default": "UTC"},
                    "format": {"type": "string", "enum": ["iso", "human", "unix"], "default": "human"}
                },
                "required": []
            }
        }
    }


def execute(timezone: str = "UTC", format: str = "human") -> dict:
    """Get current time"""
    now = datetime.utcnow()
    
    if format == "iso":
        return {"time": now.isoformat() + "Z", "timezone": timezone}
    elif format == "unix":
        return {"timestamp": int(now.timestamp()), "timezone": timezone}
    else:  # human
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day": now.strftime("%A"),
            "timezone": timezone
        }
