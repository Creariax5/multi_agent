let tamagotchi = null;

// DOM Elements
const noTamaEl = document.getElementById('no-tama');
const tamaDisplayEl = document.getElementById('tama-display');
const loadingEl = document.getElementById('loading');
const generateBtn = document.getElementById('generate-btn');

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadTamagotchi();
    generateBtn.addEventListener('click', generateTamagotchi);
    
    // Enter to talk
    document.getElementById('talk-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') talk();
    });
    
    // Decay needs every 30 seconds
    setInterval(decayNeeds, 30000);
});

function loadTamagotchi() {
    const saved = localStorage.getItem('ai-tamagotchi');
    if (saved) {
        tamagotchi = JSON.parse(saved);
        renderTamagotchi();
    }
}

function saveTamagotchi() {
    if (tamagotchi) {
        localStorage.setItem('ai-tamagotchi', JSON.stringify(tamagotchi));
    }
}

function showLoading(show) {
    loadingEl.style.display = show ? 'block' : 'none';
    if (tamagotchi) {
        tamaDisplayEl.style.display = show ? 'none' : 'block';
    } else {
        noTamaEl.style.display = show ? 'none' : 'block';
    }
}

async function generateTamagotchi() {
    showLoading(true);
    
    try {
        const response = await fetch('/api/generate', { method: 'POST' });
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur: ' + data.raw);
            showLoading(false);
            return;
        }
        
        tamagotchi = data;
        tamagotchi.created = Date.now();
        saveTamagotchi();
        renderTamagotchi();
        showMessage(tamagotchi.intro);
    } catch (error) {
        console.error(error);
        alert('Erreur de connexion');
    }
    
    showLoading(false);
}

function renderTamagotchi() {
    if (!tamagotchi) return;
    
    noTamaEl.style.display = 'none';
    tamaDisplayEl.style.display = 'block';
    
    document.getElementById('tama-emoji').textContent = tamagotchi.emoji || '🐣';
    document.getElementById('tama-name').textContent = tamagotchi.name;
    document.getElementById('tama-species').textContent = tamagotchi.species;
    document.getElementById('tama-personality').textContent = (tamagotchi.personality || []).join(' • ');
    document.getElementById('tama-level').textContent = tamagotchi.level || 1;
    
    // XP bar (100 XP per level)
    const xpPercent = ((tamagotchi.xp || 0) % 100);
    document.getElementById('xp-fill').style.width = xpPercent + '%';
    
    // Render needs
    const needsContainer = document.getElementById('tama-needs');
    needsContainer.innerHTML = '';
    
    for (const [name, value] of Object.entries(tamagotchi.needs || {})) {
        const needEl = document.createElement('div');
        needEl.className = 'need-item';
        
        const colorClass = value < 20 ? 'need-critical' : 
                          value < 40 ? 'need-low' : 
                          value < 70 ? 'need-medium' : 'need-high';
        
        needEl.innerHTML = `
            <span class="need-name">${name}</span>
            <div class="need-bar">
                <div class="need-fill ${colorClass}" style="width: ${value}%"></div>
            </div>
            <span class="need-value">${Math.round(value)}</span>
        `;
        needsContainer.appendChild(needEl);
    }
}

function showMessage(text) {
    const bubble = document.getElementById('tama-message');
    document.getElementById('message-text').textContent = text;
    bubble.style.display = 'block';
    
    // Hide after 10 seconds
    setTimeout(() => {
        bubble.style.display = 'none';
    }, 10000);
}

async function doAction(action) {
    if (!tamagotchi) return;
    showLoading(true);
    
    try {
        const response = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tamagotchi, action })
        });
        const data = await response.json();
        
        if (data.error) {
            showMessage("*fait un bruit confus*");
        } else {
            tamagotchi.needs = data.needs || tamagotchi.needs;
            addXP(data.xp_gained || 5);
            showMessage(data.response);
            saveTamagotchi();
            renderTamagotchi();
        }
    } catch (error) {
        console.error(error);
    }
    
    showLoading(false);
}

async function talk() {
    const input = document.getElementById('talk-input');
    const message = input.value.trim();
    if (!message || !tamagotchi) return;
    
    input.value = '';
    showLoading(true);
    
    try {
        const response = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tamagotchi, action: 'parler', message })
        });
        const data = await response.json();
        
        if (data.error) {
            showMessage("*te regarde sans comprendre*");
        } else {
            tamagotchi.needs = data.needs || tamagotchi.needs;
            addXP(data.xp_gained || 10);
            showMessage(data.response);
            saveTamagotchi();
            renderTamagotchi();
        }
    } catch (error) {
        console.error(error);
    }
    
    showLoading(false);
}

async function randomEvent() {
    if (!tamagotchi) return;
    showLoading(true);
    
    try {
        const response = await fetch('/api/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tamagotchi })
        });
        const data = await response.json();
        
        if (!data.error) {
            tamagotchi.needs = data.needs || tamagotchi.needs;
            addXP(data.xp_gained || 0);
            showMessage("📢 " + data.event);
            saveTamagotchi();
            renderTamagotchi();
        }
    } catch (error) {
        console.error(error);
    }
    
    showLoading(false);
}

function addXP(amount) {
    if (!tamagotchi) return;
    tamagotchi.xp = (tamagotchi.xp || 0) + amount;
    
    // Level up every 100 XP
    const newLevel = Math.floor(tamagotchi.xp / 100) + 1;
    if (newLevel > (tamagotchi.level || 1)) {
        tamagotchi.level = newLevel;
        showMessage(`🎉 Level Up! Niveau ${newLevel}!`);
    }
}

function decayNeeds() {
    if (!tamagotchi) return;
    
    // Decay each need by 1-3 points
    for (const key of Object.keys(tamagotchi.needs || {})) {
        tamagotchi.needs[key] = Math.max(0, tamagotchi.needs[key] - (Math.random() * 2 + 1));
    }
    
    saveTamagotchi();
    renderTamagotchi();
    
    // Check for critical needs
    const criticalNeeds = Object.entries(tamagotchi.needs)
        .filter(([_, v]) => v < 20)
        .map(([k, _]) => k);
    
    if (criticalNeeds.length > 0) {
        showMessage(`😰 Besoin critique: ${criticalNeeds.join(', ')}!`);
    }
}

function releaseTama() {
    if (confirm(`Tu veux vraiment libérer ${tamagotchi?.name} ?`)) {
        localStorage.removeItem('ai-tamagotchi');
        tamagotchi = null;
        tamaDisplayEl.style.display = 'none';
        noTamaEl.style.display = 'block';
        document.getElementById('tama-message').style.display = 'none';
    }
}
