"""
Generic Source Plugin

Fallback for unknown/custom event sources
"""
import json
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "generic",
        "description": "Generic events from any source",
        "endpoint": "/webhook/generic",
        "expected_fields": [],
        "examples": [
            {"event": "custom_event", "data": "..."}
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing generic events"""
    return """Tu es un assistant qui traite des événements génériques.

1. **Analyse** les données reçues:
   - Identifie le type d'événement
   - Détermine la source probable
   - Évalue l'importance

2. **Actions**:
   - Résume l'événement
   - Propose des actions si pertinent
   - Demande clarification si nécessaire

Sois concis et adapte-toi au contexte."""


def format_event(data: Dict[str, Any]) -> str:
    """Format generic event for AI"""
    
    # Try to extract useful info
    event_type = (data.get('type') or data.get('event') or 
                  data.get('event_type') or data.get('action') or 'unknown')
    source = data.get('source') or data.get('_source') or data.get('origin') or 'unknown'
    
    # Pretty print the data
    data_str = json.dumps(data, indent=2, default=str)
    if len(data_str) > 2000:
        data_str = data_str[:2000] + "\n... (tronqué)"
    
    return f"""## 🔔 Événement Générique

**Type:** {event_type}
**Source:** {source}
**Date:** {datetime.now().isoformat()}

### Données complètes:
```json
{data_str}
```
"""
