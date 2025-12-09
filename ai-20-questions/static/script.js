// Game state
let game = null;
let difficulty = 'moyen';

// Stats
let stats = JSON.parse(localStorage.getItem('20q-stats') || '{"wins":0,"games":0,"best":null}');

// DOM
const menuEl = document.getElementById('menu');
const gameEl = document.getElementById('game');
const resultEl = document.getElementById('result');
const loadingEl = document.getElementById('loading');

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateStatsDisplay();
    
    // Difficulty buttons
    document.querySelectorAll('.diff-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            difficulty = btn.dataset.diff;
        });
    });
    
    // Start button
    document.getElementById('start-btn').addEventListener('click', startGame);
    
    // Enter to ask
    document.getElementById('question-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') askQuestion();
    });
});

function showScreen(screen) {
    menuEl.style.display = 'none';
    gameEl.style.display = 'none';
    resultEl.style.display = 'none';
    loadingEl.style.display = 'none';
    
    if (screen === 'menu') menuEl.style.display = 'block';
    if (screen === 'game') gameEl.style.display = 'block';
    if (screen === 'result') resultEl.style.display = 'block';
    if (screen === 'loading') loadingEl.style.display = 'block';
}

function updateStatsDisplay() {
    document.getElementById('wins').textContent = stats.wins;
    document.getElementById('games').textContent = stats.games;
    document.getElementById('best').textContent = stats.best || '-';
}

async function startGame() {
    const category = document.getElementById('category').value;
    document.getElementById('loading-text').textContent = "L'IA choisit quelque chose...";
    showScreen('loading');
    
    try {
        const response = await fetch('/api/new-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, difficulty })
        });
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur: ' + data.raw);
            showScreen('menu');
            return;
        }
        
        game = {
            answer: data.answer,
            category: data.category,
            hint: data.hint,
            questionsLeft: 20,
            history: []
        };
        
        // Update UI
        const categoryEmojis = {
            'animal': '🐾',
            'objet': '📦',
            'personnage célèbre': '🌟',
            'lieu': '🌍',
            'film ou série': '🎬',
            'nourriture': '🍕'
        };
        const emoji = categoryEmojis[data.category] || '🎲';
        document.getElementById('game-category').textContent = `${emoji} ${data.category}`;
        document.getElementById('questions-count').textContent = '20';
        document.getElementById('hint').textContent = '💡 ' + data.hint;
        document.getElementById('history').innerHTML = '';
        document.getElementById('question-input').value = '';
        
        showScreen('game');
    } catch (error) {
        console.error(error);
        alert('Erreur de connexion');
        showScreen('menu');
    }
}

async function askQuestion() {
    if (!game || game.questionsLeft <= 0) return;
    
    const input = document.getElementById('question-input');
    const question = input.value.trim();
    if (!question) return;
    
    input.value = '';
    input.disabled = true;
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answer: game.answer,
                question: question,
                history: game.history
            })
        });
        const data = await response.json();
        
        game.questionsLeft--;
        game.history.push({ q: question, r: data.response });
        
        // Update UI
        document.getElementById('questions-count').textContent = game.questionsLeft;
        addHistoryItem(20 - game.questionsLeft, question, data.response, data.explanation);
        
        if (game.questionsLeft <= 0) {
            setTimeout(() => endGame(false), 500);
        }
    } catch (error) {
        console.error(error);
    }
    
    input.disabled = false;
    input.focus();
}

function addHistoryItem(num, question, answer, explanation) {
    const historyEl = document.getElementById('history');
    
    const answerClass = answer.toLowerCase().includes('oui') ? 'yes' : 
                       answer.toLowerCase().includes('non') ? 'no' : 'partial';
    
    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
        <span class="num">${num}</span>
        <div class="content">
            <div class="question">${question}</div>
            <div class="answer ${answerClass}">${answer}${explanation ? ' - ' + explanation : ''}</div>
        </div>
    `;
    historyEl.appendChild(item);
    historyEl.scrollTop = historyEl.scrollHeight;
}

async function makeGuess() {
    if (!game) return;
    
    const guess = prompt("Quelle est ta réponse ?");
    if (!guess) return;
    
    document.getElementById('loading-text').textContent = "Vérification...";
    showScreen('loading');
    
    try {
        const response = await fetch('/api/guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answer: game.answer,
                guess: guess
            })
        });
        const data = await response.json();
        
        if (data.correct) {
            endGame(true, 20 - game.questionsLeft + 1);
        } else {
            game.questionsLeft--;
            document.getElementById('questions-count').textContent = game.questionsLeft;
            addHistoryItem(20 - game.questionsLeft, `🎯 "${guess}"`, '❌ Non', data.message);
            
            if (game.questionsLeft <= 0) {
                endGame(false);
            } else {
                showScreen('game');
            }
        }
    } catch (error) {
        console.error(error);
        showScreen('game');
    }
}

function giveUp() {
    if (confirm("Tu veux vraiment abandonner ?")) {
        endGame(false);
    }
}

function endGame(won, questionsUsed = 20) {
    stats.games++;
    
    if (won) {
        stats.wins++;
        if (!stats.best || questionsUsed < stats.best) {
            stats.best = questionsUsed;
        }
        document.getElementById('result-icon').textContent = '🎉';
        document.getElementById('result-title').textContent = 'Bravo!';
        document.getElementById('result-message').textContent = 'Tu as trouvé!';
        document.getElementById('result-score').textContent = `En seulement ${questionsUsed} question${questionsUsed > 1 ? 's' : ''}!`;
    } else {
        document.getElementById('result-icon').textContent = '😅';
        document.getElementById('result-title').textContent = 'Perdu!';
        document.getElementById('result-message').textContent = 'La réponse était:';
        document.getElementById('result-score').textContent = '';
    }
    
    document.getElementById('result-answer').textContent = game.answer;
    
    localStorage.setItem('20q-stats', JSON.stringify(stats));
    updateStatsDisplay();
    showScreen('result');
    game = null;
}

function backToMenu() {
    showScreen('menu');
}
