"""
Tool to recall stored memories/facts.
Used for RAG - search through previously stored information.
"""
import os
import httpx

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://memory-service:8084")


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search through stored memories to find relevant information. Use this to recall user preferences, facts, or context from previous conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant memories"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional: Filter by category (general, preference, fact, task, context)"
                    },
                    "telegram_chat_id": {
                        "type": "string",
                        "description": "Optional: Filter memories for a specific user"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return (default 10)"
                    }
                },
                "required": ["query"]
            }
        }
    }


def execute(query: str, category: str = None, telegram_chat_id: str = None, limit: int = 10) -> dict:
    query = query.strip() if query else ""
    
    if not query:
        return {"success": False, "error": "Search query is required"}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "query": query,
                "limit": limit
            }
            if category:
                payload["category"] = category
            if telegram_chat_id:
                payload["telegram_chat_id"] = telegram_chat_id
            
            response = client.post(
                f"{MEMORY_SERVICE_URL}/memories/search",
                json=payload
            )
            
            if response.status_code == 200:
                memories = response.json().get("memories", [])
                
                if not memories:
                    return {
                        "success": True,
                        "found": 0,
                        "memories": [],
                        "message": "No memories found matching the query."
                    }
                
                # Format memories for output
                formatted = []
                for mem in memories:
                    formatted.append({
                        "content": mem.get("content"),
                        "category": mem.get("category"),
                        "created_at": mem.get("created_at")
                    })
                
                return {
                    "success": True,
                    "found": len(formatted),
                    "memories": formatted
                }
            else:
                error = response.json().get("detail", "Unknown error")
                return {"success": False, "error": error}
                
    except httpx.RequestError as e:
        return {"success": False, "error": f"Failed to connect to memory service: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    if result.get("success"):
        count = result.get("found", 0)
        return {
            "type": "notification",
            "content": f"🔍 {count} mémoire(s) trouvée(s)"
        }
    else:
        return {
            "type": "error",
            "content": f"❌ Erreur: {result.get('error', 'Unknown')}"
        }
