# Infinite Craft AI

A recreation of the popular "Infinite Craft" game, powered by the Multi-Agent Copilot system.

## How it works

1. **Frontend**: A simple drag-and-drop interface (HTML/JS).
2. **Backend**: A FastAPI service that handles crafting requests.
3. **AI Logic**: When two elements are combined, the backend sends a prompt to the `copilot-proxy` (GPT-4) to determine the result.

## Features

- Drag and drop elements to combine them.
- AI-generated results (names and emojis).
- Persistent discovery (saved in LocalStorage).
- Search functionality.

## Running

This service is part of the docker-compose network.
Access it at: http://localhost:3001
