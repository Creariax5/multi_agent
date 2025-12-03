"""
Event Processor - Sends events to AI for processing

Uses the plugin system from sources/ for formatting and instructions.
Integrates with memory-service to find user's telegram_chat_id.
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx

from config import COPILOT_PROXY_URL, MEMORY_SERVICE_URL, DEFAULT_MODEL
from sources import registry

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes incoming events by sending them to the AI"""
    
    def __init__(self):
        self.copilot_url = COPILOT_PROXY_URL
        self.memory_url = MEMORY_SERVICE_URL
        self.history: List[Dict] = []
        self.max_history = 100
        
        # Load source plugins
        registry.load_all()
    
    async def lookup_user_by_account(self, account_type: str, account_identifier: str) -> Optional[Dict]:
        """
        Look up a user by their linked account (e.g., email).
        Returns user info including telegram_chat_id if found.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.post(
                    f"{self.memory_url}/users/lookup-by-account",
                    json={
                        "account_type": account_type,
                        "account_identifier": account_identifier
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Lookup failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Could not lookup user: {e}")
        return None
    
    async def get_recent_messages(self, telegram_chat_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent messages for a user from memory-service.
        Used to inject conversation history for context.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.memory_url}/conversations/user/{telegram_chat_id}/recent-messages",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    return response.json().get("messages", [])
        except Exception as e:
            logger.warning(f"Could not get recent messages: {e}")
        return []
    
    async def save_message(self, telegram_chat_id: str, role: str, content: str) -> bool:
        """Save a message to memory-service."""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.post(
                    f"{self.memory_url}/conversations/message",
                    json={
                        "conversation_id": f"telegram_{telegram_chat_id}",
                        "role": role,
                        "content": content,
                        "telegram_chat_id": telegram_chat_id
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not save message: {e}")
        return False
    
    def _extract_account_identifier(self, source: str, event_data: Dict) -> Optional[tuple]:
        """
        Extract account type and identifier from event data.
        Used to look up the user in memory-service.
        """
        if source == "email":
            # Try to extract recipient email - pass raw, let AI parse if needed
            to_email = event_data.get("to") or event_data.get("recipient") or event_data.get("to_email")
            if to_email:
                # Handle list format
                if isinstance(to_email, list):
                    to_email = to_email[0] if to_email else None
                # Handle dict format with email field
                if isinstance(to_email, dict):
                    to_email = to_email.get("email") or to_email.get("address")
                if to_email:
                    # Extract email from "Name <email>" format if present
                    import re
                    match = re.search(r'<([^>]+)>', str(to_email))
                    email = match.group(1) if match else str(to_email)
                    return ("email", email.lower().strip())
        
        elif source == "slack":
            user_id = event_data.get("user") or event_data.get("user_id")
            if user_id:
                return ("slack", user_id)
        
        elif source == "calendar":
            organizer = event_data.get("organizer") or event_data.get("email")
            if organizer:
                return ("email", organizer.lower().strip())
        
        return None
    
    async def process(
        self,
        source: str,
        event_data: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an event by sending it to the AI.
        
        Args:
            source: Event source (email, stripe, slack, etc.)
            event_data: The event payload
            custom_instructions: Optional custom instructions override
            model: AI model to use
        
        Returns:
            AI response with actions taken
        """
        # Try to look up user by account
        user_info = None
        telegram_chat_id = None
        account_info = self._extract_account_identifier(source, event_data)
        
        if account_info:
            account_type, account_identifier = account_info
            user_info = await self.lookup_user_by_account(account_type, account_identifier)
            if user_info:
                telegram_chat_id = user_info.get("telegram_chat_id")
                logger.info(f"📍 Found user with chat_id: {telegram_chat_id}")
        
        # Get instructions from plugin or custom
        instructions = registry.get_instructions(source, custom_instructions)
        
        # Add telegram_chat_id context if available
        if telegram_chat_id:
            instructions += f"\n\n⚠️ IMPORTANT: L'utilisateur a un compte Telegram lié. Son chat_id est: {telegram_chat_id}\nUtilise l'outil send_telegram avec ce chat_id pour lui envoyer des notifications."
        
        # Format event using plugin
        event_content = registry.format_event(source, event_data)
        
        # Build messages - start with history if available
        messages = [{"role": "system", "content": instructions}]
        
        # Load recent conversation history for context
        if telegram_chat_id:
            recent_messages = await self.get_recent_messages(telegram_chat_id, limit=10)
            if recent_messages:
                logger.info(f"📜 Loaded {len(recent_messages)} messages from history")
                for msg in recent_messages:
                    messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add the current event as user message
        messages.append({"role": "user", "content": event_content})
        
        # Record in history
        event_record = {
            "id": len(self.history) + 1,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "event_summary": event_content[:200] + "..." if len(event_content) > 200 else event_content,
            "status": "processing"
        }
        self.history.append(event_record)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        try:
            # Call AI
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.copilot_url}/v1/chat/completions",
                    json={
                        "messages": messages,
                        "model": model or DEFAULT_MODEL,
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"AI error: {response.status_code} - {response.text}")
                
                result = response.json()
                ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Save event and response to memory for context
                if telegram_chat_id:
                    await self.save_message(telegram_chat_id, "user", event_content)
                    if ai_response:
                        await self.save_message(telegram_chat_id, "assistant", ai_response)
                
                # Update history
                event_record["status"] = "completed"
                event_record["response_summary"] = ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
                
                logger.info(f"✅ Processed {source} event successfully")
                
                return {
                    "success": True,
                    "source": source,
                    "response": ai_response,
                    "event_id": event_record["id"]
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing {source} event: {e}")
            event_record["status"] = "error"
            event_record["error"] = str(e)
            
            return {
                "success": False,
                "source": source,
                "error": str(e),
                "event_id": event_record["id"]
            }
    
    async def process_streaming(
        self,
        source: str,
        event_data: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Process an event with streaming response.
        Yields SSE events.
        """
        instructions = registry.get_instructions(source, custom_instructions)
        event_content = registry.format_event(source, event_data)
        
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": event_content}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.copilot_url}/v1/chat/completions",
                    json={
                        "messages": messages,
                        "model": model or DEFAULT_MODEL,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
                            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent event history"""
        return self.history[-limit:][::-1]


# Singleton
event_processor = EventProcessor()
