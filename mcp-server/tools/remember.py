"""
Tool to store a memory/fact that the AI should remember.
Used for RAG - the AI can recall this information later.
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")

VALID_CATEGORIES = ["general", "preference", "fact", "task", "context"]


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Store information that should be remembered for future conversations. Use this to save user preferences, important facts, or context that will be useful later. The AI can recall this information using the 'recall' tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The information to remember. Be specific and include relevant context."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the memory (general, preference, fact, task, context)",
                        "enum": VALID_CATEGORIES
                    },
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "Optional: The Telegram chat ID to associate this memory with a specific user"
                    }
                },
                "required": ["content"]
            }
        }
    }


def execute(content: str, category: str = "general", telegram_chat_id: str = None) -> dict:
    content = content.strip() if content else ""
    
    if not content:
        return {"success": False, "error": "Content is required"}
    
    if category not in VALID_CATEGORIES:
        category = "general"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "content": content,
                "category": category
            }
            if telegram_chat_id:
                payload["telegram_chat_id"] = telegram_chat_id
            
            response = client.post(
                f"{MEMORY_SERVICE_URL}/memories",
                json=payload
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Memory stored successfully in category '{category}'.",
                    "id": response.json().get("id")
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
            "content": f"🧠 Mémorisé: {args.get('content', '')[:50]}..."
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
