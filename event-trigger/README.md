# Event Trigger Service

Service de webhook qui déclenche le traitement IA pour différentes sources d'événements.

## Concept

Quand un événement arrive (email, paiement Stripe, message Slack, etc.), ce service:
1. Reçoit le webhook
2. Identifie la source
3. Applique des instructions spécifiques à cette source
4. Envoie à l'IA pour traitement
5. L'IA peut ensuite agir (répondre, créer un event, etc.) via les outils Zapier

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Sources   │────▶│  event-trigger  │────▶│  copilot-proxy  │
│             │     │                 │     │                 │
│ • Email     │     │ • Instructions  │     │ • AI Processing │
│ • Stripe    │     │ • Formatting    │     │ • Tool Calls    │
│ • Slack     │     │ • History       │     │                 │
│ • Calendar  │     │                 │     │                 │
│ • Zapier    │     │                 │     │                 │
└─────────────┘     └─────────────────┘     └─────────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  zapier-bridge  │
                                            │                 │
                                            │ • Gmail         │
                                            │ • Calendar      │
                                            │ • Slack         │
                                            │ • etc.          │
                                            └─────────────────┘
```

## Endpoints

### Webhooks

| Endpoint | Source | Description |
|----------|--------|-------------|
| `POST /webhook/{source}` | Any | Webhook générique |
| `POST /webhook/email` | Email | Notifications email |
| `POST /webhook/stripe` | Stripe | Événements paiement |
| `POST /webhook/slack` | Slack | Messages Slack |
| `POST /webhook/calendar` | Calendar | Événements calendrier |
| `POST /webhook/zapier` | Zapier | Webhooks Zapier |
| `POST /webhook/form` | Form | Soumissions formulaire |

### Autres

| Endpoint | Description |
|----------|-------------|
| `GET /` | Status du service |
| `GET /health` | Health check |
| `GET /history` | Historique des événements traités |
| `GET /instructions` | Liste des templates d'instructions |
| `GET /instructions/{source}` | Instructions pour une source |
| `POST /trigger` | Déclenchement manuel |
| `POST /trigger/sync` | Déclenchement synchrone (attend la réponse) |

## Configuration

### Variables d'environnement

```bash
COPILOT_PROXY_URL=http://copilot-proxy:8080
DEFAULT_MODEL=gpt-4.1
WEBHOOK_SECRET=your_secret  # Optionnel
ENABLED_SOURCES=email,stripe,slack,zapier,custom
```

## Exemples d'utilisation

### 1. Email via Zapier

Dans Zapier, créez un Zap:
1. **Trigger**: Gmail - New Email
2. **Action**: Webhooks by Zapier - POST
3. **URL**: `http://your-server:8083/webhook/email`
4. **Payload**:
```json
{
  "from": "{{sender}}",
  "to": "{{to}}",
  "subject": "{{subject}}",
  "body": "{{body_plain}}",
  "date": "{{date}}"
}
```

### 2. Stripe Webhook

Dans Stripe Dashboard:
1. Developers → Webhooks → Add endpoint
2. URL: `http://your-server:8083/webhook/stripe`
3. Events: `payment_intent.succeeded`, `customer.subscription.created`, etc.

### 3. Test manuel

```bash
# Test email
curl -X POST http://localhost:8083/trigger/sync \
  -H "Content-Type: application/json" \
  -d '{
    "source": "email",
    "data": {
      "from": "client@example.com",
      "subject": "Question urgente",
      "body": "Bonjour, j'\''ai une question concernant ma commande..."
    }
  }'

# Test paiement Stripe
curl -X POST http://localhost:8083/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{
    "type": "payment_intent.succeeded",
    "data": {
      "object": {
        "amount": 5000,
        "currency": "eur",
        "customer_email": "client@example.com"
      }
    }
  }'
```

## Instructions par source

Chaque source a ses propres instructions qui contextualisent le traitement IA.
Voir `instructions.py` pour les templates complets.

### Personnalisation

Vous pouvez passer des instructions custom via le paramètre `instructions`:

```bash
curl -X POST "http://localhost:8083/webhook/email?instructions=Réponds%20toujours%20en%20anglais"
```

Ou dans le body avec `/trigger`:

```json
{
  "source": "email",
  "data": {...},
  "instructions": "Réponds toujours en anglais et sois très formel"
}
```

## Flux de traitement

1. **Réception**: Le webhook arrive sur `/webhook/{source}`
2. **Validation**: Vérification du secret (si configuré)
3. **Formatage**: L'événement est formaté en message lisible
4. **Instructions**: Les instructions spécifiques à la source sont ajoutées
5. **IA**: Le message est envoyé à copilot-proxy
6. **Actions**: L'IA peut utiliser les outils Zapier pour agir
7. **Historique**: L'événement est enregistré dans l'historique

## Sécurité

### Webhook Secret

Configurez `WEBHOOK_SECRET` pour sécuriser vos endpoints:

```bash
WEBHOOK_SECRET=my_super_secret_key
```

Puis incluez-le dans vos webhooks:
- Header: `X-Webhook-Secret: my_super_secret_key`
- Ou: `Authorization: Bearer my_super_secret_key`
- Ou: Query param: `?secret=my_super_secret_key`

### Stripe Signature

Pour une sécurité maximale avec Stripe, vous pouvez vérifier la signature Stripe.
(À implémenter si nécessaire)

## Monitoring

### Voir l'historique

```bash
curl http://localhost:8083/history?limit=10
```

### Logs Docker

```bash
docker logs -f event-trigger
```
