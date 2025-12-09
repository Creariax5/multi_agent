# 🤔 AI 20 Questions

## Concept

Le classique jeu des 20 Questions, mais l'IA **génère l'objet/personne/concept à deviner** et **répond intelligemment** à tes questions.

## Gameplay

### Modes de jeu
1. **L'IA pense** : L'IA choisit quelque chose, tu poses des questions
2. **Tu penses** : Tu choisis quelque chose, l'IA pose des questions

### Mode "L'IA pense"
1. L'IA génère secrètement un objet/personne/concept
2. Tu poses des questions fermées (oui/non)
3. L'IA répond honnêtement
4. Tu as 20 questions pour deviner
5. Tu peux tenter une réponse à tout moment

### Mode "Tu penses"
1. Tu penses à quelque chose (sans le dire)
2. L'IA pose des questions stratégiques
3. Tu réponds oui/non
4. L'IA tente de deviner en moins de 20 questions

## Aspect Addictif

- **Score** : Moins de questions = plus de points
- **Catégories** : Animal, Personne célèbre, Objet, Concept, Lieu, Film/Série
- **Difficulté** : Facile (objets courants) → Difficile (concepts abstraits)
- **Streaks** : Combien de parties gagnées d'affilée
- **Historique** : Les meilleures parties

## Intelligence de l'IA

### Quand elle pense
- Elle choisit des choses intéressantes, pas trop faciles ni trop obscures
- Elle répond de façon cohérente (pas de contradictions)
- Elle peut dire "ça dépend" ou "partiellement" si la question est ambiguë

### Quand elle devine
- Questions stratégiques (division binaire optimale)
- Adaptation selon les réponses précédentes
- Résumé de ce qu'elle sait avant chaque question

## Stack Technique

- Backend : FastAPI + copilot-proxy
- Frontend : HTML/CSS/JS simple
- Stockage : localStorage pour stats et historique
- Port : 3003

## Prompts IA (exemples)

### Génération de l'objet secret
```
Choisis un [catégorie] à faire deviner en 20 questions.
Difficulté : [facile/moyen/difficile]
Retourne en JSON:
{
    "answer": "la réponse",
    "category": "catégorie",
    "hint": "un indice vague pour commencer",
    "difficulty": "facile/moyen/difficile"
}
```

### Réponse à une question
```
Tu as choisi : [réponse secrète]
Question de l'utilisateur : [question]
Réponds honnêtement en JSON:
{
    "response": "oui/non/partiellement/ça dépend",
    "explanation": "courte clarification si nécessaire"
}
```

### Vérification de la réponse
```
Réponse secrète : [réponse]
Proposition de l'utilisateur : [proposition]
Est-ce correct (même avec des formulations différentes) ?
{
    "correct": true/false,
    "message": "réaction appropriée"
}
```

## MVP Features

- [ ] Mode "L'IA pense"
- [ ] Sélection de catégorie
- [ ] Questions et réponses
- [ ] Compteur de questions (20)
- [ ] Tentative de réponse
- [ ] Score basé sur le nombre de questions
- [ ] Historique des parties

## Interface

```
┌─────────────────────────────────────┐
│          🤔 20 Questions            │
├─────────────────────────────────────┤
│  Catégorie: Animal                  │
│  Questions restantes: 15/20         │
│                                     │
│  Historique:                        │
│  1. Est-ce un mammifère? → Oui      │
│  2. Vit-il en forêt? → Non          │
│  3. Est-il domestique? → Oui        │
│  4. A-t-il des pattes? → Oui        │
│  5. Est-ce un chat? → ...           │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ Ta question...              │    │
│  └─────────────────────────────┘    │
│  [Poser la question] [Je sais!]     │
└─────────────────────────────────────┘
```
