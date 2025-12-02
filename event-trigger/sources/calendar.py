"""
Calendar Source Plugin

Handles Google Calendar, Outlook Calendar webhooks
"""
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "calendar",
        "description": "Calendar events (Google Calendar, Outlook)",
        "endpoint": "/webhook/calendar",
        "expected_fields": ["summary", "start", "end"],
        "examples": [
            {
                "summary": "Meeting with client",
                "start": "2025-12-02T14:00:00",
                "end": "2025-12-02T15:00:00"
            }
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing calendar events"""
    return """Tu es un assistant calendrier intelligent. Quand tu reçois un événement:

1. **Analyse** l'événement:
   - Type (nouveau, modifié, rappel, annulé)
   - Date et heure
   - Participants
   - Importance (récurrent, client, deadline)

2. **Actions possibles**:
   - Préparer un brief pour une réunion
   - Envoyer un rappel
   - Vérifier les conflits
   - Proposer une préparation

3. **Réponds** avec:
   - Résumé de l'événement
   - Temps restant avant l'événement
   - Actions de préparation suggérées

Sois proactif dans la préparation."""


def format_event(data: Dict[str, Any]) -> str:
    """Format calendar event for AI"""
    
    event_type = data.get('event_type') or data.get('type') or 'notification'
    summary = data.get('summary') or data.get('title') or data.get('subject') or 'Sans titre'
    
    # Handle various date formats
    start = data.get('start') or data.get('startTime') or data.get('start_time') or 'Non spécifié'
    end = data.get('end') or data.get('endTime') or data.get('end_time') or ''
    
    # If start is a dict (Google Calendar format)
    if isinstance(start, dict):
        start = start.get('dateTime') or start.get('date') or str(start)
    if isinstance(end, dict):
        end = end.get('dateTime') or end.get('date') or str(end)
    
    location = data.get('location') or data.get('where') or 'Non spécifié'
    description = data.get('description') or data.get('body') or 'Pas de description'
    
    # Participants
    attendees = data.get('attendees') or data.get('participants') or []
    if isinstance(attendees, list):
        if attendees and isinstance(attendees[0], dict):
            attendees = [a.get('email', a.get('name', str(a))) for a in attendees]
        attendees_str = ', '.join(attendees[:10]) or 'Aucun'
    else:
        attendees_str = str(attendees)
    
    # Organizer
    organizer = data.get('organizer', {})
    if isinstance(organizer, dict):
        organizer = organizer.get('email', organizer.get('name', ''))
    
    # Conference link
    conference = data.get('conferenceData', {})
    meeting_link = ''
    if conference:
        entry_points = conference.get('entryPoints', [])
        for ep in entry_points:
            if ep.get('entryPointType') == 'video':
                meeting_link = ep.get('uri', '')
                break
    meeting_link = meeting_link or data.get('hangoutLink') or data.get('meetingLink') or ''
    
    return f"""## 📅 Événement Calendrier

**Type:** {event_type}
**Titre:** {summary}
**Date:** {start}{f' - {end}' if end else ''}
**Lieu:** {location}
**Organisateur:** {organizer or 'N/A'}

### Description:
{description[:500] if description else 'Pas de description'}

### Participants:
{attendees_str}

### Lien visio:
{meeting_link or 'Aucun'}
"""
