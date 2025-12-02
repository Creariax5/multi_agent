"""
Form Source Plugin

Handles form submissions (contact forms, surveys, etc.)
"""
import json
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "form",
        "description": "Form submissions (contact, surveys, signups)",
        "endpoint": "/webhook/form",
        "expected_fields": ["variable"],
        "accepts_form_data": True,
        "examples": [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "message": "I have a question"
            }
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing form submissions"""
    return """Tu es un assistant de traitement de formulaires. Quand tu reçois une soumission:

1. **Analyse** le formulaire:
   - Type (contact, inscription, feedback, support)
   - Champs remplis
   - Urgence ou priorité

2. **Actions possibles**:
   - Répondre automatiquement si standard
   - Créer un ticket/tâche
   - Ajouter à une liste/CRM
   - Alerter si urgent

3. **Réponds** avec:
   - Résumé des informations
   - Type de formulaire détecté
   - Actions recommandées

Sois attentif aux demandes de contact."""


def format_event(data: Dict[str, Any]) -> str:
    """Format form submission for AI"""
    
    # Try to identify form type
    form_type = "général"
    if any(k in data for k in ['email', 'name', 'message']):
        form_type = "contact"
    if any(k in data for k in ['company', 'budget', 'service']):
        form_type = "lead/devis"
    if any(k in data for k in ['rating', 'feedback', 'satisfaction']):
        form_type = "feedback"
    if any(k in data for k in ['password', 'confirm', 'username']):
        form_type = "inscription"
    
    # Format all fields
    fields = []
    for key, value in data.items():
        if key.startswith('_'):  # Skip internal fields
            continue
        # Truncate long values
        str_value = str(value)
        if len(str_value) > 500:
            str_value = str_value[:500] + "..."
        fields.append(f"- **{key}:** {str_value}")
    
    fields_str = '\n'.join(fields) if fields else 'Aucun champ'
    
    # Try to get key info
    email = data.get('email') or data.get('mail') or data.get('e-mail') or 'N/A'
    name = data.get('name') or data.get('nom') or data.get('fullname') or data.get('full_name') or 'N/A'
    
    return f"""## 📝 Soumission de Formulaire

**Type détecté:** {form_type}
**Date:** {datetime.now().isoformat()}
**Email:** {email}
**Nom:** {name}

### Champs du formulaire:
{fields_str}
"""
