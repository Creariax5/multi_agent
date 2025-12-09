// Game state
let game = null;
let recentTopics = [];

// Stats
let stats = JSON.parse(localStorage.getItem('trivia-stats') || '{"bestScore":0,"bestStreak":0}');

// DOM
const menuEl = document.getElementById('menu');
const gameEl = document.getElementById('game');
const loadingEl = document.getElementById('loading');
const gameoverEl = document.getElementById('gameover');

// Category emojis
const categoryEmojis = {
    'culture générale': '🌐',
    'géographie': '🌍',
    'histoire': '📚',
    'sciences': '🔬',
    'cinéma et séries': '🎬',
    'jeux vidéo': '🎮',
    'musique': '🎵',
    'sport': '⚽',
    'gastronomie': '🍕',
    'random': '🎲'
};

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateStatsDisplay();
    
    // Category buttons
    document.querySelectorAll('.cat-btn').forEach(btn => {
        btn.addEventListener('click', () => startGame(btn.dataset.cat));
    });
    
    // Custom theme
    document.getElementById('custom-btn').addEventListener('click', () => {
        const theme = document.getElementById('custom-theme').value.trim();
        if (theme) startGame(theme, true);
    });
    
    document.getElementById('custom-theme').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const theme = e.target.value.trim();
            if (theme) startGame(theme, true);
        }
    });
});

function showScreen(screen) {
    menuEl.style.display = 'none';
    gameEl.style.display = 'none';
    loadingEl.style.display = 'none';
    gameoverEl.style.display = 'none';
    
    if (screen === 'menu') menuEl.style.display = 'block';
    if (screen === 'game') gameEl.style.display = 'block';
    if (screen === 'loading') loadingEl.style.display = 'block';
    if (screen === 'gameover') gameoverEl.style.display = 'block';
}

function updateStatsDisplay() {
    document.getElementById('best-score').textContent = stats.bestScore;
    document.getElementById('best-streak').textContent = stats.bestStreak;
}

async function startGame(category, isCustom = false) {
    game = {
        category: category,
        isCustom: isCustom,
        score: 0,
        correct: 0,
        streak: 0,
        maxStreak: 0,
        difficulty: 3
    };
    recentTopics = [];
    
    // Update UI
    const emoji = categoryEmojis[category] || '🎯';
    document.getElementById('game-category').textContent = `${emoji} ${category}`;
    document.getElementById('score').textContent = '0';
    document.getElementById('streak-display').textContent = '🔥 0';
    document.getElementById('streak-display').classList.remove('hot');
    
    await loadQuestion();
}

async function loadQuestion() {
    showScreen('loading');
    document.getElementById('feedback').style.display = 'none';
    
    try {
        const endpoint = game.isCustom ? '/api/custom-question' : '/api/question';
        const body = game.isCustom 
            ? { theme: game.category, difficulty: game.difficulty }
            : { category: game.category, difficulty: game.difficulty, recent_topics: recentTopics };
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur: ' + (data.raw || 'Impossible de générer une question'));
            showScreen('menu');
            return;
        }
        
        game.currentQuestion = data;
        if (data.topic) recentTopics.push(data.topic);
        
        displayQuestion(data);
        showScreen('game');
    } catch (error) {
        console.error(error);
        alert('Erreur de connexion');
        showScreen('menu');
    }
}

function displayQuestion(q) {
    document.getElementById('question-text').textContent = q.question;
    
    const choicesEl = document.getElementById('choices');
    choicesEl.innerHTML = '';
    
    const letters = ['A', 'B', 'C', 'D'];
    q.choices.forEach((choice, i) => {
        const btn = document.createElement('button');
        btn.className = 'choice-btn';
        btn.innerHTML = `<span class="letter">${letters[i]}</span><span>${choice}</span>`;
        btn.addEventListener('click', () => selectAnswer(i));
        choicesEl.appendChild(btn);
    });
}

function selectAnswer(index) {
    const q = game.currentQuestion;
    const buttons = document.querySelectorAll('.choice-btn');
    
    // Disable all buttons
    buttons.forEach(btn => {
        btn.classList.add('disabled');
        btn.style.pointerEvents = 'none';
    });
    
    // Mark selected
    buttons[index].classList.add('selected');
    
    // Show correct/wrong
    const isCorrect = index === q.correct;
    
    setTimeout(() => {
        buttons[q.correct].classList.add('correct');
        if (!isCorrect) {
            buttons[index].classList.add('wrong');
        }
        
        // Update game state
        if (isCorrect) {
            game.streak++;
            game.correct++;
            
            // Calculate points with streak bonus
            let points = 10;
            if (game.streak >= 10) points += 20;
            else if (game.streak >= 5) points += 10;
            else if (game.streak >= 2) points += 5;
            
            game.score += points;
            game.maxStreak = Math.max(game.maxStreak, game.streak);
            
            // Increase difficulty gradually
            if (game.correct % 3 === 0 && game.difficulty < 5) {
                game.difficulty++;
            }
        } else {
            game.streak = 0;
            // Decrease difficulty on wrong answer
            if (game.difficulty > 1) game.difficulty--;
        }
        
        // Update UI
        document.getElementById('score').textContent = game.score;
        document.getElementById('streak-display').textContent = `🔥 ${game.streak}`;
        document.getElementById('streak-display').classList.toggle('hot', game.streak >= 5);
        
        // Show feedback
        showFeedback(isCorrect, q.explanation);
    }, 500);
}

function showFeedback(isCorrect, explanation) {
    const feedbackEl = document.getElementById('feedback');
    feedbackEl.className = `feedback ${isCorrect ? 'correct' : 'wrong'}`;
    feedbackEl.style.display = 'block';
    
    document.getElementById('feedback-icon').textContent = isCorrect ? '✅' : '❌';
    document.getElementById('feedback-text').textContent = isCorrect ? 'Bonne réponse!' : 'Mauvaise réponse!';
    document.getElementById('explanation').textContent = explanation || '';
}

async function nextQuestion() {
    await loadQuestion();
}

function quitGame() {
    // Save stats
    if (game.score > stats.bestScore) stats.bestScore = game.score;
    if (game.maxStreak > stats.bestStreak) stats.bestStreak = game.maxStreak;
    localStorage.setItem('trivia-stats', JSON.stringify(stats));
    
    // Show game over
    document.getElementById('final-score').textContent = game.score;
    document.getElementById('final-correct').textContent = game.correct;
    document.getElementById('final-streak').textContent = game.maxStreak;
    
    showScreen('gameover');
    updateStatsDisplay();
}

function backToMenu() {
    showScreen('menu');
}
