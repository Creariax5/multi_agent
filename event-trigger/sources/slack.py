"""
Slack Source Plugin

Handles Slack message and event webhooks
"""
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "slack",
        "description": "Slack messages and events",
        "endpoint": "/webhook/slack",
        "expected_fields": ["text", "user", "channel"],
        "supports_challenge": True,  # Slack URL verification
        "examples": [
            {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "text": "Hello!"
            }
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing Slack messages"""
    return """Tu es un assistant Slack intelligent. Quand tu reçois un message:

1. **Analyse** le message:
   - Est-ce une question, demande, ou information?
   - Y a-t-il une mention (@) ou urgence?
   - Quel est le contexte (channel, thread)?

2. **Actions possibles**:
   - Répondre à une question
   - Créer une tâche/rappel
   - Escalader si urgent
   - Documenter si important

3. **Réponds** avec:
   - Résumé du message
   - Action recommandée ou réponse suggérée
   - Si c'est une question technique, fournis la réponse

Sois concis et adapté au ton Slack (moins formel)."""


def format_event(data: Dict[str, Any]) -> str:
    """Format Slack event for AI"""
    
    # Handle nested event structure
    event = data.get('event', data)
    
    user = event.get('user') or event.get('user_id') or event.get('user_name') or 'Inconnu'
    channel = event.get('channel') or event.get('channel_id') or event.get('channel_name') or 'DM'
    text = event.get('text') or event.get('message', {}).get('text') or 'Pas de contenu'
    ts = event.get('ts') or event.get('event_ts') or datetime.now().isoformat()
    
    # Thread info
    thread_ts = event.get('thread_ts', '')
    is_thread = bool(thread_ts)
    
    # Mentions
    is_mention = '<@' in text or event.get('is_mention', False)
    
    # Attachments
    attachments = event.get('attachments', [])
    files = event.get('files', [])
    
    attachment_info = ""
    if attachments:
        attachment_info = f"\n### Attachments:\n{len(attachments)} attachment(s)"
    if files:
        file_names = [f.get('name', 'fichier') for f in files[:5]]
        attachment_info += f"\n### Fichiers:\n{', '.join(file_names)}"
    
    return f"""## 💬 Message Slack

**De:** {user}
**Channel:** {channel}
**Date:** {ts}
**Thread:** {'Oui' if is_thread else 'Non'}
**Mention:** {'Oui' if is_mention else 'Non'}

### Message:
{text}
{attachment_info}
"""


def handle_challenge(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Slack URL verification challenge"""
    if data.get('type') == 'url_verification':
        return {"challenge": data.get('challenge')}
    return None
