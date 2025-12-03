# 📐 Contrats des Services - Référence

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONTRATS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   TRIGGERS                    CORE                      OUTPUTS              │
│   ─────────                   ────                      ───────              │
│   telegram-trigger ──┐                              ┌── telegram-sender      │
│   chat-ui-trigger ───┼── TriggerEvent ──► ai-brain ─┼── email-sender        │
│   email-trigger ─────┤         │            │       └── slack-sender        │
│   slack-trigger ─────┘         │            │                               │
│                                │            │                               │
│                                │            ├── LogEvent ──► event-log      │
│                                │            │                    │          │
│                                │            └── MemoryQuery ◄──► memory     │
│                                │                                 │          │
│   INTERFACES                   │                                 │          │
│   ──────────                   │                                 │          │
│   chat-ui ◄────────────────────┴─── stream (SSE) ────────────────┘          │
│   telegram-bot ◄───────────────────────────────────────────────────         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📨 TriggerEvent (Standard)

Tous les triggers produisent ce format:

```typescript
interface TriggerEvent {
  // Identifiants
  source: "telegram" | "chat_ui" | "email" | "slack" | "calendar" | string;
  user_id: string;           // Identifiant unique de l'utilisateur
  session_id: string;        // Format: "{source}_{user_id}_{timestamp}"
  
  // Contenu
  message: string;           // Le message/contenu principal
  
  // Contexte (optionnel, dépend de la source)
  context: {
    [key: string]: any;      // Données spécifiques à la source
  };
  
  // Options (optionnel)
  options?: {
    model?: string;          // Modèle IA à utiliser
    respond_to?: string[];   // Où envoyer les réponses ["telegram", "chat_ui"]
  };
}
```

### Exemples par source:

```json
// telegram-trigger
{
  "source": "telegram",
  "user_id": "123456",
  "session_id": "telegram_123456_1701234567",
  "message": "Bonjour !",
  "context": {
    "chat_id": "123456",
    "username": "john_doe",
    "first_name": "John"
  }
}

// chat-ui-trigger
{
  "source": "chat_ui",
  "user_id": "session_abc123",
  "session_id": "chat_ui_abc123_1701234567",
  "message": "Crée-moi une page HTML",
  "context": {},
  "options": {
    "model": "gpt-4.1"
  }
}

// email-trigger
{
  "source": "email",
  "user_id": "user@company.com",
  "session_id": "email_user_1701234567",
  "message": "Nouvel email de client@example.com\nSujet: Question urgente\n\nContenu...",
  "context": {
    "from": "client@example.com",
    "to": "user@company.com",
    "subject": "Question urgente",
    "raw_body": "..."
  }
}
```

---

## 📝 LogEvent (Standard)

Le `ai-brain` produit des LogEvents streamés vers `event-log`:

```typescript
interface LogEvent {
  // Identifiants
  id: string;                // Unique ID: "evt_{uuid}"
  type: LogEventType;
  session_id: string;
  user_id: string;
  source: string;            // Source originale du trigger
  timestamp: string;         // ISO 8601
  
  // Contenu (varie selon le type)
  data: {
    [key: string]: any;
  };
}

type LogEventType = 
  | "trigger_received"    // Trigger reçu
  | "processing_start"    // Début traitement IA
  | "thinking"            // Réflexion IA
  | "thinking_delta"      // Chunk de réflexion (streaming)
  | "tool_call"           // Appel d'un tool
  | "tool_result"         // Résultat d'un tool
  | "message"             // Message final
  | "message_delta"       // Chunk de message (streaming)
  | "artifact"            // Artifact créé
  | "artifact_edit"       // Artifact modifié
  | "send_command"        // Commande d'envoi
  | "processing_end"      // Fin traitement
  | "error";              // Erreur
```

### Exemples:

```json
// thinking (streaming)
{
  "id": "evt_abc123",
  "type": "thinking_delta",
  "session_id": "telegram_123456_1701234567",
  "user_id": "123456",
  "source": "telegram",
  "timestamp": "2025-12-03T10:00:01Z",
  "data": {
    "content": "Let me analyze"  // Chunk
  }
}

// tool_call
{
  "id": "evt_def456",
  "type": "tool_call",
  "session_id": "telegram_123456_1701234567",
  "user_id": "123456",
  "source": "telegram",
  "timestamp": "2025-12-03T10:00:02Z",
  "data": {
    "tool": "search_web",
    "arguments": {"query": "weather paris"}
  }
}

// message (final)
{
  "id": "evt_ghi789",
  "type": "message",
  "session_id": "telegram_123456_1701234567",
  "user_id": "123456",
  "source": "telegram",
  "timestamp": "2025-12-03T10:00:05Z",
  "data": {
    "content": "La météo à Paris est ensoleillée, 15°C."
  }
}

// artifact
{
  "id": "evt_jkl012",
  "type": "artifact",
  "session_id": "chat_ui_abc_1701234567",
  "user_id": "abc",
  "source": "chat_ui",
  "timestamp": "2025-12-03T10:00:10Z",
  "data": {
    "artifact_id": "art_xyz",
    "title": "Dashboard",
    "type": "html",
    "content": "<!DOCTYPE html>..."
  }
}
```

---

## 📤 SendCommand (Standard)

Le `ai-brain` envoie des commandes aux senders:

```typescript
interface SendCommand {
  target: "telegram" | "email" | "slack";
  user_id: string;
  data: TelegramSendData | EmailSendData | SlackSendData;
}

interface TelegramSendData {
  chat_id: string;
  message: string;
  parse_mode?: "HTML" | "Markdown";
}

interface EmailSendData {
  to: string;
  subject: string;
  body: string;
  html?: boolean;
}

interface SlackSendData {
  channel: string;
  message: string;
}
```

---

## 🧠 MemoryQuery (Standard)

Communication avec `memory-store`:

```typescript
// Écriture
interface MemoryWrite {
  action: "write";
  user_id?: string;          // null = global
  type: "memory" | "user" | "config";
  data: {
    category?: string;       // Pour memories: "preference", "fact", etc.
    content: string;
    [key: string]: any;
  };
}

// Lecture RAG
interface MemorySearch {
  action: "search";
  user_id?: string;
  query: string;
  limit?: number;
}

// Fast Memory
interface MemoryGetFast {
  action: "get_fast";
  user_id: string;
}

// Réponse
interface MemoryResponse {
  success: boolean;
  data?: any;
  error?: string;
}
```

---

## 🔌 Endpoints par Service

### `telegram-trigger`
```
# Reçoit (interne - polling)
Telegram API → getUpdates

# Produit
POST http://ai-brain:8080/trigger
Body: TriggerEvent
```

### `chat-ui-trigger`
```
# Reçoit
POST /trigger
Body: {message: string, session_id?: string, model?: string}

# Produit
POST http://ai-brain:8080/trigger
Body: TriggerEvent
```

### `email-trigger`
```
# Reçoit (webhook depuis n8n, etc.)
POST /webhook/email
Body: {from, to, subject, body, ...}

# Produit
POST http://ai-brain:8080/trigger
Body: TriggerEvent
```

### `ai-brain`
```
# Reçoit
POST /trigger
Body: TriggerEvent

# Produit
POST http://event-log:8085/events
Body: LogEvent

POST http://telegram-sender:8086/send
Body: SendCommand

POST http://memory-store:8084/query
Body: MemoryQuery
```

### `event-log`
```
# Reçoit
POST /events
Body: LogEvent

# Sert
GET /events/{session_id}
Response: SSE stream of LogEvent

GET /events/{session_id}/history
Response: JSON array of LogEvent
```

### `memory-store`
```
# Reçoit
POST /query
Body: MemoryQuery

# Répond
Response: MemoryResponse
```

### `telegram-sender`
```
# Reçoit
POST /send
Body: SendCommand (target: "telegram")

# Produit
Side effect: Message sur Telegram
```

### `chat-ui` (interface)
```
# Consomme
GET http://event-log:8085/events/{session_id}
→ SSE stream

# Affiche
Browser WebSocket/SSE → UI
```

---

## 🐳 docker-compose.yml

```yaml
services:
  # === TRIGGERS ===
  telegram-trigger:
    build: ./triggers/telegram
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - AI_BRAIN_URL=http://ai-brain:8080

  chat-ui-trigger:
    build: ./triggers/chat-ui
    ports: ["3001:3001"]
    environment:
      - AI_BRAIN_URL=http://ai-brain:8080

  email-trigger:
    build: ./triggers/email
    ports: ["8083:8083"]
    environment:
      - AI_BRAIN_URL=http://ai-brain:8080

  # === CORE ===
  ai-brain:
    build: ./core/ai-brain
    ports: ["8080:8080"]
    environment:
      - COPILOT_TOKEN=${COPILOT_TOKEN}
      - EVENT_LOG_URL=http://event-log:8085
      - MEMORY_URL=http://memory-store:8084
      - TELEGRAM_SENDER_URL=http://telegram-sender:8086

  event-log:
    build: ./core/event-log
    ports: ["8085:8085"]
    volumes:
      - event_data:/app/data

  memory-store:
    build: ./core/memory-store
    ports: ["8084:8084"]
    volumes:
      - memory_data:/app/data

  # === SENDERS ===
  telegram-sender:
    build: ./senders/telegram
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

  # === INTERFACES ===
  chat-ui:
    build: ./interfaces/chat-ui
    ports: ["3000:3000"]
    environment:
      - TRIGGER_URL=http://chat-ui-trigger:3001
      - EVENT_LOG_URL=http://event-log:8085

volumes:
  event_data:
  memory_data:
```

---

## 📁 Structure des dossiers

```
multi_agent/
├── triggers/
│   ├── telegram/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── chat-ui/
│   │   └── ...
│   └── email/
│       └── ...
│
├── core/
│   ├── ai-brain/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── loop.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── think.py
│   │   │   └── ...
│   │   └── requirements.txt
│   ├── event-log/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   └── memory-store/
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
│
├── senders/
│   ├── telegram/
│   │   └── ...
│   └── email/
│       └── ...
│
├── interfaces/
│   ├── chat-ui/
│   │   ├── Dockerfile
│   │   ├── static/
│   │   └── templates/
│   └── telegram-bot/
│       └── ...
│
└── docker-compose.yml
```
