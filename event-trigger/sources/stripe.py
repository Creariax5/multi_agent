"""
Stripe Source Plugin

Handles Stripe webhook events (payments, subscriptions, etc.)
"""
import json
from datetime import datetime
from typing import Dict, Any


def get_definition() -> Dict:
    """Return source definition"""
    return {
        "name": "stripe",
        "description": "Stripe payment webhooks",
        "endpoint": "/webhook/stripe",
        "expected_fields": ["type", "data.object"],
        "examples": [
            {
                "type": "payment_intent.succeeded",
                "data": {"object": {"amount": 5000, "currency": "eur"}}
            }
        ]
    }


def get_instructions() -> str:
    """Return AI instructions for processing Stripe events"""
    return """Tu es un assistant de gestion des paiements Stripe. Quand tu reçois un événement:

1. **Analyse** l'événement:
   - Type (paiement réussi, échoué, abonnement, remboursement, etc.)
   - Montant et devise
   - Client concerné

2. **Actions selon le type**:
   - **payment_intent.succeeded**: Confirmer la commande, envoyer reçu
   - **payment_intent.failed**: Alerter, proposer alternatives
   - **customer.subscription.created**: Activer accès, email bienvenue
   - **customer.subscription.deleted**: Désactiver accès, email rétention
   - **charge.refunded**: Confirmer remboursement
   - **invoice.payment_failed**: Relancer le paiement

3. **Réponds** avec:
   - Résumé de l'événement
   - Actions prises ou recommandées
   - Alertes si problème

Sois précis sur les montants et les clients."""


def format_event(data: Dict[str, Any]) -> str:
    """Format Stripe webhook event for AI"""
    
    event_type = data.get('type', 'unknown')
    event_id = data.get('id', 'N/A')
    
    # Get the nested object
    obj = data.get('data', {}).get('object', data.get('object', data))
    
    # Parse amount (Stripe uses cents)
    amount = obj.get('amount') or obj.get('amount_total') or obj.get('amount_paid') or 0
    if isinstance(amount, (int, float)) and amount > 0:
        amount = amount / 100
    
    currency = (obj.get('currency') or 'eur').upper()
    
    # Customer info
    customer = obj.get('customer', '')
    customer_email = obj.get('receipt_email') or obj.get('customer_email') or obj.get('email', 'N/A')
    
    # Additional details based on event type
    details = []
    
    if 'subscription' in event_type:
        details.append(f"- **Plan:** {obj.get('plan', {}).get('nickname', obj.get('plan', {}).get('id', 'N/A'))}")
        details.append(f"- **Interval:** {obj.get('plan', {}).get('interval', 'N/A')}")
        details.append(f"- **Status:** {obj.get('status', 'N/A')}")
    
    if 'invoice' in event_type:
        details.append(f"- **Invoice ID:** {obj.get('id', 'N/A')}")
        details.append(f"- **Paid:** {obj.get('paid', False)}")
        details.append(f"- **Billing Reason:** {obj.get('billing_reason', 'N/A')}")
    
    if obj.get('metadata'):
        meta = obj['metadata']
        if isinstance(meta, dict):
            for k, v in list(meta.items())[:5]:
                details.append(f"- **{k}:** {v}")
    
    details_str = '\n'.join(details) if details else 'Aucun détail supplémentaire'
    
    # Truncate raw data for context
    raw_preview = json.dumps(obj, indent=2, default=str)[:800]
    
    return f"""## 💳 Événement Stripe

**Type:** {event_type}
**ID:** {event_id}
**Date:** {datetime.now().isoformat()}

### Informations principales:
- **Montant:** {amount} {currency}
- **Client ID:** {customer or 'N/A'}
- **Email:** {customer_email}
- **Status:** {obj.get('status', 'N/A')}
- **Description:** {obj.get('description', 'N/A')}

### Détails:
{details_str}

### Données brutes (extrait):
```json
{raw_preview}
```
"""
