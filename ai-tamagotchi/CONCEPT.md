# 🐣 AI Tamagotchi

## Concept

Un animal de compagnie virtuel où **tout est généré par l'IA** : son apparence, sa personnalité, ses besoins, ses réactions.

## Gameplay

### Création
1. Tu décris ton animal (ou l'IA te propose un random)
2. L'IA génère :
   - **Nom** (généré)
   - **Espèce** (peut être fantastique)
   - **Personnalité** (timide, joueur, glouton...)
   - **Apparence** (description textuelle + emoji)
   - **Besoins uniques** (pas juste faim/sommeil)

### Boucle de jeu
- Ton Tamagotchi a des **jauges dynamiques** (générées par l'IA selon sa personnalité)
- Tu peux lui **parler** (l'IA répond en character)
- Tu peux **faire des actions** (nourrir, jouer, etc.)
- L'IA génère des **événements aléatoires** (il a trouvé un objet, il est malade, etc.)
- Ton Tamagotchi **évolue** avec le temps

### Évolution
- Après X interactions, l'IA fait évoluer ton Tamagotchi
- Nouvelle apparence, nouveaux besoins, nouvelle personnalité
- Les évolutions dépendent de comment tu l'as traité

## Aspect Addictif

- **Notifications** : "Ton Tamagotchi s'ennuie !"
- **Progression visible** : Level, évolutions
- **Collection** : Historique de tous tes Tamagotchis
- **Mort** : Si tu l'ignores trop longtemps, il peut partir
- **Surprise** : Chaque Tamagotchi est unique

## Stack Technique

- Backend : FastAPI + copilot-proxy pour générer
- Frontend : HTML/CSS/JS simple
- Stockage : localStorage pour l'état du Tamagotchi
- Port : 3002

## Prompts IA (exemples)

### Génération initiale
```
Génère un Tamagotchi unique avec :
- nom (créatif)
- espèce (réelle ou fantastique)
- emoji représentatif
- personnalité (3 traits)
- 4 besoins avec noms uniques et valeurs 0-100
- une phrase d'introduction
Retourne en JSON.
```

### Réponse à une action
```
Tu es [nom], un [espèce] [personnalité].
Tes besoins actuels : [besoins]
L'utilisateur fait : [action]
Génère ta réaction (courte, en character) et les nouveaux niveaux de besoins.
```

### Événement aléatoire
```
Tu es [nom], un [espèce] [personnalité].
Génère un petit événement aléatoire qui lui arrive.
Retourne l'événement et l'impact sur ses besoins.
```

## MVP Features

- [ ] Génération d'un Tamagotchi
- [ ] Affichage état (emoji + jauges)
- [ ] Actions de base (nourrir, jouer, parler)
- [ ] Réponses IA en character
- [ ] Sauvegarde localStorage
- [ ] Timer de décroissance des besoins
