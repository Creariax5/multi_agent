# Multi-Agent Copilot Chat

A Claude-like chat interface powered by GitHub Copilot with MCP (Model Context Protocol) tools support.

## Architecture Principles

### 🎯 Microservices First (Anti-Monolithic)
- **One service = One responsibility**: Each feature should be its own isolated service
- **Loose coupling**: Services communicate via HTTP APIs, not shared code
- **Independent deployment**: Each service can be updated without affecting others
- **Separate containers**: Every service runs in its own Docker container

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

## Project Structure

```
multi_agent/
├── chat-ui/           # Frontend Flask application (port 3000)
│   ├── main.py        # FastAPI server
│   ├── static/
│   │   ├── js/        # Modular JavaScript
│   │   │   ├── app.js          # Main application logic
│   │   │   ├── artifact.js     # Artifact panel management
│   │   │   ├── conversations.js # Conversation state
│   │   │   ├── event-handlers.js # SSE event processing
│   │   │   ├── sse-parser.js   # SSE stream parsing
│   │   │   └── utils.js        # Utility functions
│   │   ├── style.css
│   │   └── artifact.css
│   └── templates/
│       └── index.html
├── copilot-proxy/     # Agentic proxy server (port 8080)
│   └── main.py        # Tool execution loop
├── mcp-server/        # MCP tool server (port 8081)
│   ├── main.py
│   └── tools/         # Tool implementations
│       ├── think.py
│       ├── send_message.py
│       ├── create_artifact.py
│       ├── web_search.py
│       └── ...
└── docker-compose.yaml
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

## Adding New Tools

1. Create a new Python file in `mcp-server/tools/`
2. Implement `get_definition()`, `execute()`, and optionally `to_event()`
3. The tool is auto-discovered on server restart
