# 📚 Documentation Restructuration

Cette documentation explore différentes architectures pour réorganiser le projet multi-agent.

## Documents

| Fichier | Description |
|---------|-------------|
| [01-VISION-ORIGINALE.md](./01-VISION-ORIGINALE.md) | Vision initiale clarifiée |
| [02-ANALYSE-CRITIQUE.md](./02-ANALYSE-CRITIQUE.md) | Analyse des forces/faiblesses |
| [03-PROPOSITION-ULTRA-SIMPLE.md](./03-PROPOSITION-ULTRA-SIMPLE.md) | Proposition A: 2 services |
| [04-PROPOSITION-EVENT-SOURCING.md](./04-PROPOSITION-EVENT-SOURCING.md) | Proposition B: Event Sourcing |
| [05-PROPOSITION-MONOLITHE-MODULAIRE.md](./05-PROPOSITION-MONOLITHE-MODULAIRE.md) | Proposition C: Monolithe (obsolète) |
| [06-PROPOSITION-SERVERLESS.md](./06-PROPOSITION-SERVERLESS.md) | Proposition D: Serverless |
| [07-RECOMMANDATION-FINALE.md](./07-RECOMMANDATION-FINALE.md) | ~~Ancienne reco~~ (obsolète) |
| [08-PROPOSITION-SERVICES-MODULAIRES.md](./08-PROPOSITION-SERVICES-MODULAIRES.md) | Proposition E: Services modulaires |
| [09-CONTRATS-SERVICES.md](./09-CONTRATS-SERVICES.md) | Contrats INPUT/OUTPUT |
| [10-ARCHITECTURE-FINALE.md](./10-ARCHITECTURE-FINALE.md) | **🏆 ARCHITECTURE FINALE** |

## TL;DR

**Architecture choisie: Tout passe par les logs. Les services observent et réagissent.**

```
TRIGGERS ──► AI-BRAIN ──► EVENT-LOG ◄── OBSERVERS
                              │
                              └── (stream SSE)
```

### Principe clé

1. **Triggers** reçoivent des messages → envoient `TriggerEvent` à ai-brain
2. **AI-Brain** traite et émet **tous** les events vers event-log
3. **Observers** lisent le stream et réagissent :
   - `memory-store` stocke les events `memory_write`
   - `telegram-bot` envoie quand il voit `send_telegram`
   - `chat-ui` affiche en temps réel

### Les 7 services

| Catégorie | Services | Rôle |
|-----------|----------|------|
| **Triggers** | `telegram-trigger`, `chat-ui-trigger` | Reçoivent → TriggerEvent |
| **Core** | `ai-brain`, `event-log` | Traitement + logs centraux |
| **Observers** | `memory-store`, `chat-ui`, `telegram-bot` | Observent et réagissent |

### Un seul format : LogEvent

```typescript
{
  type: "message" | "thinking" | "send_telegram" | "memory_write" | ...,
  session_id: string,
  user_id: string,
  source: "telegram" | "chat_ui" | ...,
  data: any
}
```

## Quick Start

```bash
docker compose up
```

Pour ajouter un nouveau canal (ex: Discord):
1. Créer `triggers/discord/` → envoie TriggerEvent à ai-brain
2. Créer `observers/discord-bot/` → observe event-log et envoie
3. C'est tout ! 🎉
