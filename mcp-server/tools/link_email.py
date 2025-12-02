"""
Tool to link an email address to the current user's Telegram chat.
This allows the AI to send notifications to the user when emails arrive.
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "link_email",
            "description": "Link an email address to the user's Telegram chat. This allows the AI to send notifications when emails arrive at this address. The user must provide their email address. The telegram_chat_id is automatically provided by the system context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The email address to link"
                    },
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "The Telegram chat ID (automatically injected by the system, do not ask the user)"
                    }
                },
                "required": ["email"]
            }
        }
    }


def execute(email: str, telegram_chat_id: str) -> dict:
    email = email.strip().lower() if email else ""
    
    if not email:
        return {"success": False, "error": "Email address is required"}
    
    if not telegram_chat_id:
        return {"success": False, "error": "Telegram chat ID is required"}
    
    # Basic email validation
    if "@" not in email or "." not in email:
        return {"success": False, "error": "Invalid email address format"}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MEMORY_SERVICE_URL}/accounts/link",
                json={
                    "telegram_chat_id": telegram_chat_id,
                    "account_type": "email",
                    "account_identifier": email
                }
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Email {email} has been linked to your Telegram chat. You will now receive notifications when emails arrive at this address."
                }
            else:
                error = response.json().get("detail", "Unknown error")
                return {"success": False, "error": error}
                
    except httpx.RequestError as e:
        return {"success": False, "error": f"Failed to connect to memory service: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    if result.get("success"):
        return {
            "type": "notification",
            "content": f"✅ Email lié: {args.get('email')}"
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
