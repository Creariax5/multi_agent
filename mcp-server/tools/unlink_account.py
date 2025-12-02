"""
Tool to unlink an account from the user's profile.
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "unlink_account",
            "description": "Remove a linked account (email, slack, etc.) from the user's profile. Use this when the user wants to stop receiving notifications for a specific account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "The Telegram chat ID of the user"
                    },
                    "account_type": {
                        "type": "string",
                        "description": "Type of account to unlink (email, slack, etc.)"
                    },
                    "account_identifier": {
                        "type": "string",
                        "description": "The account identifier (email address, slack user ID, etc.)"
                    }
                },
                "required": ["telegram_chat_id", "account_type", "account_identifier"]
            }
        }
    }


def execute(telegram_chat_id: str, account_type: str, account_identifier: str) -> dict:
    if not telegram_chat_id:
        return {"success": False, "error": "Telegram chat ID is required"}
    
    account_type = account_type.lower() if account_type else ""
    if not account_type:
        return {"success": False, "error": "Account type is required"}
    
    if not account_identifier:
        return {"success": False, "error": "Account identifier is required"}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MEMORY_SERVICE_URL}/accounts/unlink",
                json={
                    "telegram_chat_id": telegram_chat_id,
                    "account_type": account_type,
                    "account_identifier": account_identifier
                }
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Account {account_identifier} ({account_type}) has been unlinked from your profile."
                }
            else:
                error = response.json().get("detail", "Account not found")
                return {"success": False, "error": error}
                
    except httpx.RequestError as e:
        return {"success": False, "error": f"Failed to connect to memory service: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    if result.get("success"):
        return {
            "type": "notification",
            "content": f"🔓 Compte délié: {args.get('account_identifier')}"
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
