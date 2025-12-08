# Multi-Agent Copilot Chat

A Claude-like chat interface powered by GitHub Copilot with MCP (Model Context Protocol) tools support.

> **📐 Architecture Reference**: See `docs/restructuration/18-ARCHITECTURE-V3-FINALE.md`

## Architecture Principles

### 🎯 Microservices First (Anti-Monolithic)
- **One service = One responsibility**: Each feature should be its own isolated service
- **Loose coupling**: Services communicate via HTTP APIs, not shared code
- **Independent deployment**: Each service can be updated without affecting others
- **Separate containers**: Every service runs in its own Docker container

### 💡 No Duplication - Single Source of Truth
- `event-log` stores EVERYTHING (conversations, tool calls, memories, artifacts)
- `memory` is just an indexing layer on top of event-log (embeddings only)

### ☝️ One Service = One Exact Responsibility
Each service does **ONE thing only**. If you can't describe what a service does in one sentence, split it.

#### Core Services (5)
| Service | Responsibility ONLY | Port |
|---------|---------------------|------|
| `ai-brain` | Orchestrate the agentic loop | 8080 |
| `copilot-client` | Connect to GitHub Copilot (token, streaming) | 8081 |
| `mcp-server` | Execute tools (plugins) | 8082 |
| `prompt-builder` | Build prompts from context | 8083 |
| `event-log` | Store and stream ALL events (single source of truth) | 8085 |

#### Auxiliary Services
| Service | Responsibility | Port |
|---------|----------------|------|
| `memory` | Index events + semantic search (no data duplication) | 8084 |

#### Interface Services (3 per interface)
| Service Type | Responsibility | Example |
|--------------|----------------|---------|
| `*-trigger` | Receive external input → TriggerEvent | `telegram-trigger` |
| `*-observer` | Listen to event-log → call sender | `telegram-observer` |
| `*-sender` | Send message to external service | `telegram-sender` |

**Rule**: If a service does 2 things, create 2 services.

**Why separate Core?**
- Copilot down → error in `copilot-client`, not elsewhere
- Tool crash → error in `mcp-server`, isolated logs
- Infinite loop → it's `ai-brain`, easy to debug
- New LLM provider → change only `copilot-client`

### 📐 Strict Interface Templates
Every interface (telegram, chat-ui, email, etc.) **MUST** follow the exact same structure.
The system validates structure at startup and **fails if non-compliant**.

Required structure for each interface:
```
interfaces/{name}/
├── trigger/
│   ├── main.py          # Must expose FastAPI app
│   └── requirements.txt
├── observer/
│   ├── main.py          # Must connect to event-log SSE
│   └── requirements.txt
└── sender/
    ├── main.py          # Must expose POST /send
    └── requirements.txt
```

**All use the same Dockerfile**: `interfaces/_base/Dockerfile.template`

Use `interfaces/_template/` as base. Copy, don't create from scratch.

### 🔌 Plugin Systems Everywhere
- **Normalize extensibility**: Use plugin patterns whenever a category of features can grow
- **Auto-discovery**: Plugins should be auto-discovered at startup (scan folders)
- **Standard interface**: Each plugin type has a clear interface (get_definition, execute, etc.)
- **No code modification**: Adding a feature = adding a file, not modifying existing code

Plugin patterns in use:
- `core/mcp-server/tools/` - AI tools (think, send_message, etc.)

Example plugin interface:
```python
# Every tool plugin must implement:
def get_definition() -> dict:    # OpenAI function schema
    ...
def execute(**args) -> dict:     # Main logic
    ...
# Optional:
def to_event(args, result) -> dict:  # Convert to LogEvent
    ...
def is_terminal() -> bool:           # True if ends the loop
    ...
```

### 🐳 100% Dockerized
- **NEVER install anything locally** - Everything runs in Docker containers
- **No local Python/Node/etc.** - Use Docker for all development and testing
- **docker-compose for orchestration** - All services defined in `docker-compose.yml`
- **Test inside containers** - Run tests via `docker exec` or dedicated test containers

Example commands:
```bash
# Run the project
docker-compose up --build

# Run a command inside a container
docker exec -it mcp-server python -c "print('test')"

# Add a new dependency - edit requirements.txt, then rebuild
docker-compose build mcp-server
```

## Key Features

- **Artifacts Panel**: Create and display HTML, code, or markdown in a side panel (like Claude)
- **MCP Tools**: Extensible tool system with think, send_message, web_search, etc.
- **Streaming**: Real-time SSE streaming with thinking deltas
- **Conversation History**: Local storage persistence

## Running the Project

```bash
docker compose up --build
```

Access at http://localhost:3000

## Adding New Features

### Adding a Tool (AI capability)
1. Create a new Python file in `core/mcp-server/tools/`
2. Implement `get_definition()`, `execute()`, and optionally `to_event()`
3. The tool is auto-discovered on server restart

### Adding a new Interface (ex: Discord)
1. Copy `interfaces/_template/` to `interfaces/discord/`
2. Implement the 3 `main.py` files (trigger, observer, sender)
3. Add the 3 services to `docker-compose.yml`
4. Create the `send_discord` tool in `mcp-server/tools/`
