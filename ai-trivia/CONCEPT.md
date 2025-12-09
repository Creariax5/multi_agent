# 🧠 AI Trivia / Quiz

## Concept

Un jeu de quiz infini où **l'IA génère les questions à la volée** sur n'importe quel sujet. Pas de base de données de questions, tout est créé dynamiquement.

## Gameplay

### Déroulement
1. Tu choisis une **catégorie** (ou random)
2. L'IA génère une question avec **4 choix**
3. Tu réponds
4. L'IA te dit si c'est correct + **explication**
5. Prochaine question!

### Catégories (exemples)
- 🌍 Géographie
- 📚 Histoire
- 🔬 Sciences
- 🎬 Cinéma & Séries
- 🎮 Jeux vidéo
- 🎵 Musique
- ⚽ Sport
- 🍕 Gastronomie
- 🌐 Culture générale
- 🎲 Random (toutes catégories)

### Modes de jeu
- **Infini** : Joue tant que tu veux, compte les bonnes réponses
- **Survie** : 3 vies, game over après 3 erreurs
- **Contre la montre** : Maximum de bonnes réponses en 2 minutes

## Aspect Addictif

- **Score en temps réel** : Points par bonne réponse
- **Streak** : Bonus pour réponses consécutives correctes
- **Leaderboard local** : Meilleurs scores par catégorie
- **Explications** : Tu apprends quelque chose à chaque question
- **Difficulté adaptative** : Plus tu réponds bien, plus c'est dur

## Intelligence de l'IA

### Génération de questions
- Questions variées (pas de répétitions)
- Difficulté adaptée au niveau
- Réponses crédibles (pas de pièges évidents)
- Une seule bonne réponse

### Explications
- Toujours une explication après la réponse
- Fun facts additionnels
- Contexte historique/culturel

## Stack Technique

- Backend : FastAPI + copilot-proxy
- Frontend : HTML/CSS/JS simple
- Stockage : localStorage pour scores
- Port : 3004

## Prompts IA (exemples)

### Génération de question
```
Génère une question de quiz sur: [catégorie]
Difficulté: [1-5]
Évite ces thèmes récents: [liste]

Retourne en JSON:
{
    "question": "la question",
    "choices": ["A", "B", "C", "D"],
    "correct": 0-3 (index de la bonne réponse),
    "explanation": "explication de la réponse + fun fact",
    "difficulty": 1-5
}

Les mauvaises réponses doivent être crédibles!
```

### Vérification (si réponse libre)
```
Question: [question]
Bonne réponse: [réponse attendue]
Réponse du joueur: [réponse]

Est-ce correct (accepte les variations)?
```

## MVP Features

- [ ] Sélection de catégorie
- [ ] Génération de questions IA
- [ ] 4 choix de réponses
- [ ] Feedback correct/incorrect
- [ ] Explication après chaque réponse
- [ ] Score et streak
- [ ] Mode infini
- [ ] Sauvegarde des meilleurs scores

## Interface

```
┌─────────────────────────────────────┐
│          🧠 AI Trivia               │
├─────────────────────────────────────┤
│  Catégorie: 🌍 Géographie           │
│  Score: 150 pts | Streak: 🔥5       │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ Quelle est la capitale du   │    │
│  │ Burkina Faso ?              │    │
│  └─────────────────────────────┘    │
│                                     │
│  [A] Bamako                         │
│  [B] Ouagadougou        ← selected  │
│  [C] Niamey                         │
│  [D] Abidjan                        │
│                                     │
│         [Valider]                   │
└─────────────────────────────────────┘
```

## Bonus: Mode "Thème libre"

L'utilisateur peut taper un thème personnalisé:
- "Harry Potter"
- "La cuisine italienne"
- "Les années 80"
- "Elon Musk"

Et l'IA génère des questions sur ce thème spécifique!

## Scoring

| Action | Points |
|--------|--------|
| Bonne réponse | +10 pts |
| Streak x2-4 | +5 bonus |
| Streak x5-9 | +10 bonus |
| Streak x10+ | +20 bonus |
| Mauvaise réponse | Streak reset |
