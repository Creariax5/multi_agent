# Zapier Bridge

Ce service fait le pont entre votre MCP server et Zapier MCP, permettant d'utiliser plus de 8000+ intégrations Zapier comme tools.

## Configuration

### 1. Créer un serveur MCP sur Zapier

1. Allez sur [mcp.zapier.com](https://mcp.zapier.com/)
2. Cliquez sur **"+ New MCP Server"**
3. Sélectionnez **"Other"** comme client AI
4. Donnez un nom à votre serveur (ex: "Multi-Agent System")
5. Cliquez sur **"Create MCP Server"**

### 2. Ajouter des actions/tools

1. Sur la page de votre serveur MCP, cliquez sur **"+ Add tool"**
2. Recherchez une app (ex: "Slack", "Google Sheets", "Gmail")
3. Sélectionnez l'action souhaitée (ex: "Send Channel Message")
4. Connectez votre compte si demandé
5. Configurez les champs (certains peuvent être laissés pour l'AI)
6. Sauvegardez

Répétez pour chaque action souhaitée.

### 3. Obtenir l'URL et le Secret

1. Allez dans l'onglet **"Connect"** de votre serveur MCP
2. Copiez l'URL MCP (format: `https://mcp.zapier.com/api/mcp/mcp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

Pour le secret (si vous utilisez l'embedding):
1. Allez sur [mcp.zapier.com/manage/embed/secrets](https://mcp.zapier.com/manage/embed/secrets)
2. Générez ou copiez votre secret

### 4. Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet:

```bash
ZAPIER_MCP_URL=https://mcp.zapier.com/api/mcp/mcp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ZAPIER_MCP_SECRET=votre_secret_ici
```

Ou exportez-les directement:

```bash
export ZAPIER_MCP_URL="https://mcp.zapier.com/api/mcp/mcp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export ZAPIER_MCP_SECRET="votre_secret_ici"
```

### 5. Relancer les services

```bash
docker-compose up --build -d
```

## Vérification

### Vérifier la connexion Zapier Bridge

```bash
curl http://localhost:8082/
# Devrait retourner: {"status":"ok","zapier_enabled":true,"zapier_connected":true}
```

### Voir les tools Zapier disponibles

```bash
curl http://localhost:8082/tools
# Liste les tools en format OpenAI
```

### Vérifier depuis MCP Server

```bash
curl http://localhost:8081/tools/zapier
# Liste les tools Zapier intégrés
```

## Comment ça marche

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Chat UI    │────▶│ Copilot Proxy│────▶│  MCP Server  │────▶│ Zapier Bridge│
│  / Telegram  │     │              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │  Zapier MCP  │
                                                               │    Server    │
                                                               └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │ 8000+ Apps   │
                                                               │ Slack, Gmail │
                                                               │ Sheets, etc. │
                                                               └──────────────┘
```

1. L'agent demande au MCP Server les tools disponibles
2. MCP Server combine les tools locaux + les tools Zapier
3. Quand un tool Zapier est appelé (préfixé `zapier_`), MCP Server le forward au Zapier Bridge
4. Zapier Bridge utilise le protocole MCP pour appeler Zapier
5. Zapier exécute l'action dans l'app cible (Slack, Gmail, etc.)

## Exemples d'utilisation

Une fois configuré, vous pouvez demander à l'agent:

- "Envoie un message sur Slack dans le channel #general"
- "Ajoute une ligne dans ma Google Sheet avec ces données"
- "Envoie un email via Gmail à john@example.com"
- "Crée une tâche dans Asana"

Les tools Zapier apparaîtront avec le préfixe `zapier_`, par exemple:
- `zapier_slack_send_channel_message`
- `zapier_google_sheets_create_spreadsheet_row`
- `zapier_gmail_send_email`

## Coûts

⚠️ Chaque appel de tool Zapier consomme **2 tasks** de votre quota Zapier.
Voir [Zapier Pricing](https://zapier.com/pricing) pour les détails.

## Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Status et connexion |
| `/tools` | GET | Liste des tools (format OpenAI) |
| `/tools/raw` | GET | Liste des tools (format MCP) |
| `/execute` | POST | Exécuter un tool |
| `/refresh` | POST | Rafraîchir le cache des tools |
| `/health` | GET | Health check |
