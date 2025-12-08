# 🏛️ Philosophie d'Architecture : SPET

> **S**ingle-responsibility | **P**lugin-first | **E**vent-driven | **T**emplate-based

---

## 📖 Définition

Cette architecture combine 4 principes fondamentaux pour créer un système **modulaire**, **extensible** et **maintenable**.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPET ARCHITECTURE                            │
├─────────────────┬─────────────────┬─────────────────┬──────────┤
│  Single-Resp.   │  Plugin-First   │  Event-Driven   │ Template │
│                 │                 │                 │          │
│ 1 service =     │ Extensible via  │ Communication   │ Patterns │
│ 1 fonction      │ fichiers, pas   │ découplée via   │ réutili- │
│                 │ code modifié    │ event-log       │ sables   │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
```

---

## 🎯 Pilier 1 : Single-Responsibility

### Principe
> **"Si tu ne peux pas décrire ce que fait un service en UNE phrase, sépare-le."**

### Application

| ❌ Mauvais | ✅ Bon |
|-----------|--------|
| `ai-brain` fait la loop + streaming LLM + exécution tools | `ai-brain` orchestre la loop |
| | `copilot-client` connecte au LLM |
| | `mcp-server` exécute les tools |

### Bénéfices
- **Debug isolé** : Une erreur = un service
- **Remplacement facile** : Changer le LLM = changer 1 service
- **Scaling ciblé** : Scaler ce qui a besoin

### Règle de validation
```
Pour chaque service, répondre à :
"Ce service fait _____ et RIEN d'autre."

Si la phrase contient "et" → séparer
```

---

## 🔌 Pilier 2 : Plugin-First

### Principe
> **"Ajouter une feature = ajouter un fichier, pas modifier du code."**

### Application

```
mcp-server/tools/
├── think.py           # Plugin 1
├── send_message.py    # Plugin 2
├── send_telegram.py   # Plugin 3
└── nouveau_tool.py    # ← Ajouter ici, rien à modifier ailleurs
```

### Interface standard
```python
# Chaque plugin DOIT implémenter :
def get_definition() -> dict:    # Schéma OpenAI
    ...
def execute(**args) -> dict:     # Logique
    ...

# OPTIONNEL :
def to_event(args, result) -> dict:  # Conversion en LogEvent
    ...
def is_terminal() -> bool:           # Termine la loop ?
    ...
```

### Bénéfices
- **Zéro régression** : Nouveau code isolé
- **Contribution facile** : Un fichier = une PR
- **Tests unitaires** : Chaque plugin testable seul

---

## 📡 Pilier 3 : Event-Driven

### Principe
> **"Les services ne se connaissent pas. Ils émettent et réagissent aux events."**

### Application

```
ai-brain ──emit──► event-log ◄──observe── telegram-observer
                      │
                      ├──observe── chatui-observer
                      │
                      └──observe── memory-observer
```

### Types d'events (LogEvent)
```typescript
type LogEventType =
  | "trigger"        // Début de requête
  | "thinking"       // Raisonnement IA
  | "message"        // Message pour l'user
  | "tool_call"      // Appel d'outil
  | "artifact"       // Création d'artifact
  | "send_telegram"  // Notification Telegram
  | "send_email"     // Notification Email
  | "memory_write"   // Écriture mémoire
  | "done"           // Fin de traitement
  | "error";         // Erreur
```

### Bénéfices
- **Découplage total** : Ajouter un observer sans toucher ai-brain
- **Replay possible** : Events stockés = rejouables
- **Temps réel** : SSE pour streaming

---

## 📐 Pilier 4 : Template-Based

### Principe
> **"Chaque interface suit le même pattern. Copier, pas inventer."**

### Le pattern Interface (3 services)

```
interfaces/{name}/
├── trigger/     # Reçoit → TriggerEvent → ai-brain
├── observer/    # Écoute event-log → filtre → sender
└── sender/      # Reçoit SendRequest → envoie externe
```

### Dockerfile unique
```dockerfile
# interfaces/_base/Dockerfile.template
# Utilisé par TOUS les trigger/observer/sender
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || true
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Bénéfices
- **Cohérence** : Toutes les interfaces identiques
- **Onboarding rapide** : Apprendre 1 pattern = comprendre tout
- **Moins d'erreurs** : Copier un template qui marche

---

## 🧮 Formules Clés

### Nombre de containers
```
Total = Core + Interfaces

Core = 6 services (après séparation memory)
Interfaces = 3 × N

Exemple : Telegram + Chat-UI + Email
= 6 + (3 × 3) = 15 containers
```

### Complexité de debug
```
Avant (monolithe) : O(n) - chercher dans tout le code
Après (SPET)      : O(1) - aller directement au bon service
```

### Temps d'ajout d'une feature
```
Nouveau tool     : 1 fichier (mcp-server/tools/)
Nouvelle interface : 3 fichiers + docker-compose
Nouveau LLM      : 1 service (remplacer copilot-client)
```

---

## ⚖️ Trade-offs

### Ce qu'on gagne
| Aspect | Bénéfice |
|--------|----------|
| Maintenabilité | Chaque service petit et compréhensible |
| Extensibilité | Plugins sans modifier l'existant |
| Debug | Erreur → service identifié immédiatement |
| Équipe | Travail parallèle sans conflits |

### Ce qu'on perd (accepté)
| Aspect | Coût | Pourquoi acceptable |
|--------|------|---------------------|
| Latence | +5ms par appel HTTP | Négligeable vs temps LLM (~500ms) |
| Complexité infra | Plus de containers | Docker Compose gère tout |
| Overhead mémoire | Chaque service = RAM | Containers légers (Python slim) |

---

## 🎨 Représentation visuelle

```
                    ┌─────────────────────────────────────┐
                    │           INTERFACES                │
                    │  ┌─────────┐ ┌─────────┐ ┌────────┐│
                    │  │Telegram │ │ Chat-UI │ │ Email  ││
                    │  │T│O│S    │ │T│O│S    │ │T│O│S   ││
                    │  └─────────┘ └─────────┘ └────────┘│
                    └──────────┬──────────────────┬──────┘
                               │                  │
                    ┌──────────▼──────────────────▼──────┐
                    │              CORE                   │
                    │  ┌──────────┐    ┌───────────────┐ │
                    │  │ ai-brain │◄──►│copilot-client │ │
                    │  └────┬─────┘    └───────────────┘ │
                    │       │                            │
                    │       ▼                            │
                    │  ┌──────────┐    ┌───────────────┐ │
                    │  │mcp-server│    │ prompt-builder│ │
                    │  └────┬─────┘    └───────────────┘ │
                    │       │                            │
                    │       ▼                            │
                    │  ┌─────────────────────────────┐   │
                    │  │         event-log           │   │
                    │  │    ┌───────┐ ┌────────┐     │   │
                    │  │    │ store │ │ stream │     │   │
                    │  │    └───────┘ └────────┘     │   │
                    │  └─────────────────────────────┘   │
                    │                                    │
                    │  ┌─────────────────────────────┐   │
                    │  │       memory (interface)    │   │
                    │  │  ┌──────┐┌──────┐┌────────┐ │   │
                    │  │  │store ││search││observer│ │   │
                    │  │  └──────┘└──────┘└────────┘ │   │
                    │  └─────────────────────────────┘   │
                    └────────────────────────────────────┘
```

---

## ✅ Checklist de conformité SPET

Pour chaque nouveau service, vérifier :

- [ ] **S** : Fait-il UNE seule chose ?
- [ ] **P** : Peut-on l'étendre via plugins/fichiers ?
- [ ] **E** : Communique-t-il via events (pas d'appels directs) ?
- [ ] **T** : Suit-il un template existant ?

Si une case n'est pas cochée → repenser le design.

---

## 📚 Références

- **Martin Fowler** : Microservices patterns
- **Alistair Cockburn** : Hexagonal Architecture (inspiration)
- **Event Sourcing** : Greg Young (inspiration pour event-log)
- **Plugin Architecture** : Eclipse, VS Code (inspiration)
