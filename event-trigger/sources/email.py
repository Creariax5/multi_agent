"""
Email Source Plugin

Handles email webhooks from Gmail, Outlook, n8n, etc.
"""
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "email",
        "description": "Email notifications (Gmail, Outlook, etc.)",
        "endpoint": "/webhook/email",
        "expected_fields": ["from", "to", "subject", "body"],
        "examples": [
            {
                "from": "client@example.com",
                "subject": "Question urgente",
                "body": "Bonjour, j'ai une question..."
            }
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing emails"""
    return """Tu es un assistant email intelligent. Quand tu reçois un email:

1. **Analyse** le contenu et détermine:
   - L'urgence (haute/moyenne/basse)
   - Le type (question, demande, information, spam)

2. **Action OBLIGATOIRE**:
   - Utilise l'outil send_telegram pour envoyer un résumé sur Telegram
   - Format du message: "📧 [Expéditeur]: [Résumé en 10 mots max]"
   
3. **Réponds** avec:
   - Confirmation que le résumé a été envoyé sur Telegram

Sois très concis."""


def format_event(data: Dict[str, Any]) -> str:
    """Format email event for AI"""
    
    # Handle various email formats
    sender = data.get('from') or data.get('sender') or data.get('from_email') or 'Inconnu'
    recipient = data.get('to') or data.get('recipient') or data.get('to_email') or 'Moi'
    subject = data.get('subject') or data.get('title') or 'Sans sujet'
    body = (data.get('body') or data.get('text') or 
            data.get('content') or data.get('html') or 'Pas de contenu')
    date = data.get('date') or data.get('timestamp') or datetime.now().isoformat()
    attachments = data.get('attachments') or data.get('files') or []
    
    # Clean HTML if present
    if '<' in body and '>' in body:
        import re
        body = re.sub(r'<[^>]+>', '', body)
        body = body.strip()[:2000]  # Limit length
    
    attachment_list = ', '.join(attachments) if isinstance(attachments, list) else str(attachments)
    
    return f"""## 📧 Nouvel Email Reçu

**De:** {sender}
**À:** {recipient}
**Sujet:** {subject}
**Date:** {date}

### Contenu:
{body}

### Pièces jointes:
{attachment_list or 'Aucune'}
"""
