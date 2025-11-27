// State
let conversations = [];
let currentConversation = null;
let messages = [];
let isLoading = false;

// DOM Elements
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const modelSelect = document.getElementById('model-select');
const conversationsContainer = document.getElementById('conversations');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    autoResize(messageInput);
    
    // Restore last selected model
    const savedModel = localStorage.getItem('selectedModel');
    if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
        modelSelect.value = savedModel;
    }
    
    // Save model selection
    modelSelect.addEventListener('change', () => {
        localStorage.setItem('selectedModel', modelSelect.value);
        // Update current conversation model if exists
        if (currentConversation) {
            currentConversation.model = modelSelect.value;
            saveConversations();
        }
    });
});

// Auto-resize textarea
function autoResize(textarea) {
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    });
}

// Handle Enter key
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || isLoading) return;

    // Clear welcome message
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    const userMessage = { role: 'user', content };
    messages.push(userMessage);
    renderMessage(userMessage);

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Show loading
    isLoading = true;
    sendBtn.disabled = true;
    const loadingEl = showLoading();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: messages,
                model: modelSelect.value
            })
        });

        const data = await response.json();
        
        // Remove loading
        loadingEl.remove();

        if (data.error) {
            showError(data.error);
        } else {
            const assistantMessage = { role: 'assistant', content: data.content };
            messages.push(assistantMessage);
            renderMessage(assistantMessage);
            
            // Save conversation
            saveConversation();
        }
    } catch (error) {
        loadingEl.remove();
        showError('Erreur de connexion au serveur');
    }

    isLoading = false;
    sendBtn.disabled = false;
    messageInput.focus();
}

// Render message
function renderMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.role}`;
    
    const avatar = message.role === 'user' ? '👤' : '🤖';
    
    // Parse markdown for assistant messages
    let content = message.content;
    if (message.role === 'assistant') {
        content = marked.parse(content);
    } else {
        content = escapeHtml(content).replace(/\n/g, '<br>');
    }
    
    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${content}</div>
    `;
    
    messagesContainer.appendChild(div);
    
    // Highlight code blocks
    div.querySelectorAll('pre code').forEach(block => {
        hljs.highlightElement(block);
    });
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Show loading indicator
function showLoading() {
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return div;
}

// Show error
function showError(message) {
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.innerHTML = `
        <div class="message-avatar">⚠️</div>
        <div class="message-content" style="color: #ff6b6b;">${escapeHtml(message)}</div>
    `;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// New chat
function newChat() {
    messages = [];
    currentConversation = null;
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h1>🤖 Copilot Chat</h1>
            <p>Posez-moi une question ou commencez une conversation.</p>
        </div>
    `;
    updateConversationsList();
}

// Save conversation
function saveConversation() {
    if (messages.length === 0) return;
    
    const title = messages[0].content.substring(0, 30) + (messages[0].content.length > 30 ? '...' : '');
    
    if (currentConversation === null) {
        currentConversation = {
            id: Date.now(),
            title,
            messages: [...messages],
            model: modelSelect.value,
            createdAt: new Date().toISOString()
        };
        conversations.unshift(currentConversation);
    } else {
        currentConversation.messages = [...messages];
        currentConversation.updatedAt = new Date().toISOString();
    }
    
    saveConversations();
    updateConversationsList();
}

// Save all conversations to localStorage
function saveConversations() {
    localStorage.setItem('conversations', JSON.stringify(conversations));
}

// Load conversations
function loadConversations() {
    const saved = localStorage.getItem('conversations');
    if (saved) {
        try {
            conversations = JSON.parse(saved);
            updateConversationsList();
        } catch (e) {
            console.error('Error loading conversations:', e);
            conversations = [];
        }
    }
}

// Update conversations list
function updateConversationsList() {
    conversationsContainer.innerHTML = conversations.map(conv => `
        <div class="conversation-item ${currentConversation?.id === conv.id ? 'active' : ''}" 
             onclick="loadConversation(${conv.id})"
             title="${escapeHtml(conv.title)}">
            <span class="conv-title">${escapeHtml(conv.title)}</span>
            <button class="delete-conv-btn" onclick="event.stopPropagation(); deleteConversation(${conv.id})" title="Supprimer">
                ×
            </button>
        </div>
    `).join('');
}

// Delete conversation
function deleteConversation(id) {
    if (!confirm('Supprimer cette conversation ?')) return;
    
    conversations = conversations.filter(c => c.id !== id);
    saveConversations();
    
    if (currentConversation?.id === id) {
        newChat();
    } else {
        updateConversationsList();
    }
}

// Load conversation
function loadConversation(id) {
    const conv = conversations.find(c => c.id === id);
    if (!conv) return;
    
    currentConversation = conv;
    messages = [...conv.messages];
    
    // Restore model for this conversation
    if (conv.model && modelSelect.querySelector(`option[value="${conv.model}"]`)) {
        modelSelect.value = conv.model;
    }
    
    messagesContainer.innerHTML = '';
    messages.forEach(msg => renderMessage(msg));
    
    updateConversationsList();
    
    // Scroll to bottom after loading
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
