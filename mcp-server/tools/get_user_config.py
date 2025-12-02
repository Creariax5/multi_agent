"""
Tool to get the current user's configuration (linked accounts, trigger settings).
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "get_user_config",
            "description": "Get the user's current configuration including linked accounts and trigger settings. Use this to show the user what accounts are linked and how their notifications are configured.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "The Telegram chat ID of the user"
                    }
                },
                "required": ["telegram_chat_id"]
            }
        }
    }


def execute(telegram_chat_id: str) -> dict:
    if not telegram_chat_id:
        return {"success": False, "error": "Telegram chat ID is required"}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Get linked accounts
            accounts_response = client.get(
                f"{MEMORY_SERVICE_URL}/accounts/{telegram_chat_id}"
            )
            
            # Get trigger configs
            triggers_response = client.get(
                f"{MEMORY_SERVICE_URL}/triggers/{telegram_chat_id}"
            )
            
            accounts = accounts_response.json().get("accounts", []) if accounts_response.status_code == 200 else []
            triggers = triggers_response.json().get("configs", []) if triggers_response.status_code == 200 else []
            
            # Format accounts nicely
            linked_accounts = []
            for acc in accounts:
                linked_accounts.append({
                    "type": acc.get("account_type"),
                    "identifier": acc.get("account_identifier"),
                    "verified": acc.get("verified", False)
                })
            
            # Format triggers
            trigger_configs = []
            for trig in triggers:
                trigger_configs.append({
                    "source": trig.get("source_type"),
                    "enabled": bool(trig.get("enabled")),
                    "instructions": trig.get("instructions")
                })
            
            return {
                "success": True,
                "linked_accounts": linked_accounts,
                "trigger_configs": trigger_configs,
                "summary": f"You have {len(linked_accounts)} linked account(s) and {len(trigger_configs)} trigger configuration(s)."
            }
                
    except httpx.RequestError as e:
        return {"success": False, "error": f"Failed to connect to memory service: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    if result.get("success"):
        accounts = result.get("linked_accounts", [])
        triggers = result.get("trigger_configs", [])
        content = f"📋 **Configuration**\n\n"
        content += f"**Comptes liés ({len(accounts)}):**\n"
        for acc in accounts:
            content += f"  • {acc['type']}: {acc['identifier']}\n"
        content += f"\n**Triggers ({len(triggers)}):**\n"
        for trig in triggers:
            status = "✅" if trig['enabled'] else "❌"
            content += f"  • {status} {trig['source']}"
            if trig.get('instructions'):
                content += f" - {trig['instructions'][:50]}..."
            content += "\n"
        return {
            "type": "message",
            "content": content
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
