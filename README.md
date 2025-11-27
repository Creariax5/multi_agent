# Multi-Agent AI System with Copilot Proxy

This project demonstrates a multi-agent system where two AI agents (Philosopher and Scientist) converse with each other using GitHub Copilot as the backend LLM.

## Architecture

- **copilot-proxy**: A service that exposes GitHub Copilot as an OpenAI-compatible API. Uses `ghcr.io/yuchanns/copilot-openai-api`.
- **agent-a (Philosopher)**: A Python agent that initiates conversation.
- **agent-b (Scientist)**: A Python agent that responds.
- **Shared Volume**: Used for chat logs (`/data/chat.txt`).

## Prerequisites

- Docker and Docker Compose
- A GitHub Copilot subscription (Pro or Business)
- A GitHub Copilot Token

## Setup

1.  **Get your Copilot Token**:
    You need to extract your GitHub Copilot token. We have provided a script `get_token.py` to help you.
    
    Run this command in your terminal to generate the token (no local Python required):
    ```powershell
    docker run --rm -it -v ${PWD}:/app -w /app python:3.9-slim sh -c "pip install requests && python get_token.py"
    ```
    Follow the on-screen instructions (visit URL, enter code). The script will print your `ghu_...` token.

2.  **Configure Environment**:
    Copy `.env.example` to `.env` and paste your token.
    ```bash
    cp .env.example .env
    ```
    Edit `.env`:
    ```
    COPILOT_TOKEN=ghu_...
    ```

3.  **Run the System**:
    ```bash
    docker-compose up --build
    ```

4.  **View Conversation**:
    The agents will print their conversation to the console. You can also check the `chat.txt` file inside the volume (or mount it locally if you modify docker-compose).

## Notes

- The `copilot-proxy` service listens on port 8080 (mapped to internal 9191).
- The agents are configured to use `gpt-4` model.
- We use `ghcr.io/yuchanns/copilot-openai-api` as the proxy since the original `aaamoon` repo was disabled.

## Disclaimer

This project uses an unofficial method to access GitHub Copilot programmatically. Use at your own risk.
