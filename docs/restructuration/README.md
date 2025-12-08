# 📚 Documentation Restructuration

## 🏆 Document de Référence

| Document | Description |
|----------|-------------|
| **[18-ARCHITECTURE-V3-FINALE.md](./18-ARCHITECTURE-V3-FINALE.md)** | 🏆 **Version Finale** - Architecture simplifiée |

## Documents Complémentaires

| Document | Description |
|----------|-------------|
| [14-ARCHITECTURE-PHILOSOPHY.md](./14-ARCHITECTURE-PHILOSOPHY.md) | Philosophie SPET, principes |
| [15-AI-PERSPECTIVE.md](./15-AI-PERSPECTIVE.md) | Point de vue de l'IA, tools, workflow |
| [16-SERVICE-SEPARATIONS.md](./16-SERVICE-SEPARATIONS.md) | Analyse des séparations de services |
| [17-CLARIFICATIONS.md](./17-CLARIFICATIONS.md) | Clarifications event-log, prompt-builder, memory |

---

## Historique des Propositions

| Fichier | Status | Description |
|---------|--------|-------------|
| 01 à 09 | 📜 Historique | Propositions successives |
| 10-12 | ⚠️ Obsolète | Remplacé par 13 |
| 13-ARCHITECTURE-V2-FINALE | ⚠️ Obsolète | Remplacé par 18 (V3) |
| **14 à 18** | ✅ **ACTIFS** | Documents de référence |

---

## 🏛️ TL;DR : Architecture V3

### Insight Clé : Pas de Duplication

- `event-log` = **source de vérité unique** (stocke TOUT)
- `memory` = juste une **couche d'indexation** (embeddings)

```
core/ (5 services)
├── ai-brain/               # Orchestration boucle
├── copilot-client/         # Connexion LLM  
├── mcp-server/tools/       # Exécution tools (plugins)
├── prompt-builder/         # Construction prompts
└── event-log/              # Stockage UNIQUE + stream SSE

services/ (1 service auxiliaire)
└── memory/                 # Indexation + recherche (pas de duplication)

interfaces/{name}/ (3 services chacun)
├── trigger/                # Reçoit → TriggerEvent → ai-brain
├── observer/               # SSE event-log → appelle sender
└── sender/                 # Envoie sur le canal externe
```

### Principes clés

1. **1 service = 1 responsabilité exacte**
2. **Pas de duplication** - event-log contient tout
3. **Extensible via plugins/fichiers**
4. **Communication via event-log SSE**
5. **Dockerfile générique** pour toutes les interfaces

### Containers : 5 (core) + 1 (memory) + 3 × N (interfaces)

| Interfaces | Total containers |
|------------|------------------|
| 2 (telegram, chat-ui) | 5 + 1 + 6 = 12 |
| 3 (+email) | 5 + 1 + 9 = 15 |
| 4 (+discord) | 5 + 1 + 12 = 18 |
