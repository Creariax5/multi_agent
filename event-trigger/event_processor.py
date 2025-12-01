"""
Event Processor - Sends events to AI for processing
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx

from config import COPILOT_PROXY_URL, DEFAULT_MODEL
from instructions import get_instructions

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes incoming events by sending them to the AI"""
    
    def __init__(self):
        self.copilot_url = COPILOT_PROXY_URL
        self.history: List[Dict] = []  # Keep last N processed events
        self.max_history = 100
    
    def _format_event_content(self, source: str, event_data: Dict[str, Any]) -> str:
        """Format event data into a readable message for the AI"""
        
        if source == "email":
            return self._format_email(event_data)
        elif source == "stripe":
            return self._format_stripe(event_data)
        elif source == "slack":
            return self._format_slack(event_data)
        elif source == "calendar":
            return self._format_calendar(event_data)
        else:
            return self._format_generic(source, event_data)
    
    def _format_email(self, data: Dict) -> str:
        """Format email event"""
        return f"""## 📧 Nouvel Email Reçu

**De:** {data.get('from', 'Inconnu')}
**À:** {data.get('to', 'Moi')}
**Sujet:** {data.get('subject', 'Sans sujet')}
**Date:** {data.get('date', datetime.now().isoformat())}

### Contenu:
{data.get('body', data.get('text', data.get('content', 'Pas de contenu')))}

### Pièces jointes:
{', '.join(data.get('attachments', [])) or 'Aucune'}
"""
    
    def _format_stripe(self, data: Dict) -> str:
        """Format Stripe webhook event"""
        event_type = data.get('type', 'unknown')
        obj = data.get('data', {}).get('object', data)
        
        amount = obj.get('amount', 0)
        if isinstance(amount, int):
            amount = amount / 100  # Stripe amounts are in cents
        
        return f"""## 💳 Événement Stripe

**Type:** {event_type}
**ID:** {data.get('id', 'N/A')}
**Date:** {datetime.now().isoformat()}

### Détails:
- **Montant:** {amount} {obj.get('currency', 'EUR').upper()}
- **Client:** {obj.get('customer', obj.get('customer_email', 'N/A'))}
- **Email:** {obj.get('receipt_email', obj.get('customer_email', 'N/A'))}
- **Description:** {obj.get('description', 'N/A')}
- **Status:** {obj.get('status', 'N/A')}

### Données brutes:
```json
{json.dumps(obj, indent=2, default=str)[:1000]}
```
"""
    
    def _format_slack(self, data: Dict) -> str:
        """Format Slack message event"""
        return f"""## 💬 Message Slack

**De:** {data.get('user', data.get('user_name', 'Inconnu'))}
**Channel:** {data.get('channel', data.get('channel_name', 'DM'))}
**Date:** {data.get('ts', datetime.now().isoformat())}

### Message:
{data.get('text', data.get('message', 'Pas de contenu'))}

### Contexte:
- Thread: {data.get('thread_ts', 'Non')}
- Mention: {data.get('is_mention', False)}
"""
    
    def _format_calendar(self, data: Dict) -> str:
        """Format calendar event"""
        return f"""## 📅 Événement Calendrier

**Type:** {data.get('event_type', 'notification')}
**Titre:** {data.get('summary', data.get('title', 'Sans titre'))}
**Date:** {data.get('start', 'Non spécifié')} - {data.get('end', '')}
**Lieu:** {data.get('location', 'Non spécifié')}

### Description:
{data.get('description', 'Pas de description')}

### Participants:
{', '.join(data.get('attendees', [])) or 'Aucun'}
"""
    
    def _format_generic(self, source: str, data: Dict) -> str:
        """Format generic event"""
        return f"""## 🔔 Événement {source.upper()}

**Source:** {source}
**Date:** {datetime.now().isoformat()}

### Données:
```json
{json.dumps(data, indent=2, default=str)}
```
"""
    
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
            custom_instructions: Optional custom instructions
            model: AI model to use
        
        Returns:
            AI response with actions taken
        """
        # Get instructions for this source
        instructions = get_instructions(source, custom_instructions)
        
        # Format event content
        event_content = self._format_event_content(source, event_data)
        
        # Build messages
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": event_content}
        ]
        
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
        instructions = get_instructions(source, custom_instructions)
        event_content = self._format_event_content(source, event_data)
        
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
