"""
Send Telegram Tool - Send messages via Telegram Bot API
"""
import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_DEFAULT_CHAT_ID = os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "")

# NOTE: Telegram API should be accessed WITHOUT proxy
# The proxy is for internal corporate network only


def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": "Send a message to Telegram. Use this to notify the user on their phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send"
                    },
                    "chat_id": {
                        "type": "string",
                        "description": "Optional: Telegram chat ID. If not provided, uses the default chat."
                    }
                },
                "required": ["message"]
            }
        }
    }


def execute(message: str, chat_id: str = None) -> dict:
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    
    # Use provided chat_id or default
    target_chat_id = chat_id or TELEGRAM_DEFAULT_CHAT_ID
    
    if not target_chat_id:
        # Try to get the last chat from updates
        target_chat_id = _get_last_chat_id()
    
    if not target_chat_id:
        return {"success": False, "error": "No chat_id provided and no default configured. Send a message to the bot first."}
    
    try:
        # Direct connection without proxy for Telegram API
        with httpx.Client(timeout=30.0) as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = client.post(url, json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "HTML"
            })
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return {
                        "success": True,
                        "message": "Message sent to Telegram",
                        "chat_id": target_chat_id
                    }
                else:
                    return {"success": False, "error": result.get("description", "Unknown error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_last_chat_id() -> str:
    """Try to get the last chat ID from recent updates"""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    try:
        # Direct connection without proxy
        with httpx.Client(timeout=10.0) as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            response = client.get(url, params={"limit": 1, "offset": -1})
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") and result.get("result"):
                    update = result["result"][0]
                    # Try different message types
                    msg = update.get("message") or update.get("edited_message") or update.get("callback_query", {}).get("message")
                    if msg and msg.get("chat"):
                        return str(msg["chat"]["id"])
    except:
        pass
    
    return None


def to_event(args: dict, result: dict) -> dict:
    """Transform tool call into UI event"""
    if result.get("success"):
        return {
            "type": "notification",
            "content": f"📱 Message envoyé sur Telegram"
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur Telegram: {result.get('error', 'Unknown')}"
        }


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
