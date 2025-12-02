"""
Tool to configure trigger settings for a user.
Allows enabling/disabling triggers and setting custom instructions.
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")

VALID_SOURCES = ["email", "stripe", "slack", "calendar", "form", "generic"]


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "set_trigger",
            "description": "Configure how the AI responds to specific event triggers. You can enable/disable notifications for a source (email, stripe, slack, calendar, form) and set custom instructions for how to handle events from that source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "The Telegram chat ID of the user"
                    },
                    "source": {
                        "type": "string",
                        "description": "The event source to configure (email, stripe, slack, calendar, form, generic)",
                        "enum": VALID_SOURCES
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable notifications for this source"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Custom instructions for how to handle events from this source. For example: 'Only notify me for urgent emails' or 'Summarize payment notifications briefly'"
                    }
                },
                "required": ["telegram_chat_id", "source"]
            }
        }
    }


def execute(telegram_chat_id: str, source: str, enabled: bool = True, instructions: str = None) -> dict:
    if not telegram_chat_id:
        return {"success": False, "error": "Telegram chat ID is required"}
    
    source = source.lower() if source else ""
    if source not in VALID_SOURCES:
        return {"success": False, "error": f"Invalid source. Must be one of: {', '.join(VALID_SOURCES)}"}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MEMORY_SERVICE_URL}/triggers/config",
                json={
                    "telegram_chat_id": telegram_chat_id,
                    "source_type": source,
                    "enabled": enabled,
                    "instructions": instructions
                }
            )
            
            if response.status_code == 200:
                status = "enabled" if enabled else "disabled"
                message = f"Trigger for '{source}' has been {status}."
                if instructions:
                    message += f" Custom instructions: \"{instructions}\""
                return {"success": True, "message": message}
            else:
                error = response.json().get("detail", "Unknown error")
                return {"success": False, "error": error}
                
    except httpx.RequestError as e:
        return {"success": False, "error": f"Failed to connect to memory service: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    if result.get("success"):
        return {
            "type": "notification",
            "content": f"⚙️ Trigger {args.get('source')} configuré"
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
