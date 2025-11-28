/**
 * Chat Application - Main entry point
 */

// DOM Elements
let messagesContainer, messageInput, sendBtn, modelSelect, useToolsCheckbox, conversationsContainer;
let isLoading = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    messagesContainer = document.getElementById('messages');
    messageInput = document.getElementById('message-input');
    sendBtn = document.getElementById('send-btn');
    modelSelect = document.getElementById('model-select');
    useToolsCheckbox = document.getElementById('use-tools');
    conversationsContainer = document.getElementById('conversations');

    // Initialize managers
    ConversationManager.init();
    ArtifactManager.init();

    // Setup UI
    Utils.autoResize(messageInput);
    restoreSettings();
    updateConversationsList();

    // Event listeners
    modelSelect.addEventListener('change', saveSettings);
    useToolsCheckbox.addEventListener('change', saveSettings);
});

function restoreSettings() {
    const savedModel = localStorage.getItem('selectedModel');
    if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
        modelSelect.value = savedModel;
    }
    const savedTools = localStorage.getItem('useTools');
    if (savedTools !== null) {
        useToolsCheckbox.checked = savedTools === 'true';
    }
}

function saveSettings() {
    localStorage.setItem('selectedModel', modelSelect.value);
    localStorage.setItem('useTools', useToolsCheckbox.checked);
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || isLoading) return;

    // Clear welcome
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    const userMessage = { role: 'user', content };
    ConversationManager.addMessage(userMessage);
    renderMessage(userMessage);

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Setup loading state
    isLoading = true;
    sendBtn.disabled = true;

    // Create assistant container
    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'message assistant';
    assistantDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="events-container"></div>
            <div class="response-text"><span class="streaming-cursor">▊</span></div>
        </div>
    `;
    messagesContainer.appendChild(assistantDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    const eventsContainer = assistantDiv.querySelector('.events-container');
    const responseDiv = assistantDiv.querySelector('.response-text');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: ConversationManager.messages,
                model: modelSelect.value,
                use_tools: useToolsCheckbox.checked
            })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        // Initialize handlers
        EventHandlers.init(eventsContainer, messagesContainer, responseDiv);

        // Parse SSE stream
        const parser = new SSEParser(
            (event) => EventHandlers.handle(event),
            (error) => console.error('SSE Error:', error)
        );
        await parser.processStream(response);

        // Finalize
        const result = EventHandlers.finalize();
        
        if (result.content || result.events.length > 0) {
            ConversationManager.addMessage({
                role: 'assistant',
                content: result.content,
                tool_calls: result.toolCalls.length > 0 ? result.toolCalls : undefined,
                events: result.events.length > 0 ? result.events : undefined
            });
        }

    } catch (error) {
        responseDiv.innerHTML = `<span style="color: #ff6b6b;">Erreur: ${Utils.escapeHtml(error.message)}</span>`;
    }

    isLoading = false;
    sendBtn.disabled = false;
    messageInput.focus();
}

function renderMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.role}`;
    const avatar = message.role === 'user' ? '👤' : '🤖';

    if (message.role === 'assistant' && message.events?.length > 0) {
        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="events-container"></div>
            </div>
        `;
        const container = div.querySelector('.events-container');
        
        message.events.forEach(event => {
            if (event.type === 'thinking') {
                container.appendChild(createThinkingBlockForRender(event.content));
            } else if (event.type === 'artifact') {
                container.appendChild(createArtifactIndicatorForRender(event));
            } else if (event.type === 'tool_call') {
                container.appendChild(createToolCallForRender(event.tool_call));
            } else if (event.type === 'text') {
                const textDiv = document.createElement('div');
                textDiv.className = 'response-text-block';
                textDiv.innerHTML = marked.parse(event.content);
                container.appendChild(textDiv);
            }
        });
    } else {
        const content = message.role === 'assistant' 
            ? marked.parse(message.content || '')
            : Utils.escapeHtml(message.content).replace(/\n/g, '<br>');
        
        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="response-text">${content}</div>
            </div>
        `;
    }

    messagesContainer.appendChild(div);
    div.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function createThinkingBlockForRender(content) {
    const div = document.createElement('div');
    div.className = 'thinking-block';
    div.innerHTML = `
        <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
            <span class="thinking-icon">💭</span>
            <span class="thinking-label">Réflexion</span>
            <span class="thinking-toggle">▼</span>
        </div>
        <div class="thinking-content">${marked.parse(content)}</div>
    `;
    return div;
}

function createArtifactIndicatorForRender(event) {
    const artifactId = event.artifactId || ArtifactManager.generateId();
    ArtifactManager.save(artifactId, {
        title: event.title,
        content: event.content,
        artifact_type: event.artifact_type
    });

    const div = document.createElement('div');
    div.className = 'artifact-indicator';
    div.innerHTML = `
        <div class="artifact-indicator-header">
            <span class="artifact-icon">📄</span>
            <span class="artifact-name">${Utils.escapeHtml(event.title)}</span>
            <span class="artifact-action">Voir →</span>
        </div>
    `;
    div.onclick = () => {
        const art = ArtifactManager.get(artifactId);
        if (art) ArtifactManager.render(art.title, art.content, art.artifact_type);
    };
    return div;
}

function createToolCallForRender(tc) {
    const div = document.createElement('div');
    div.className = 'tool-call';
    div.onclick = function() { this.classList.toggle('expanded'); };

    let resultParsed, argsParsed;
    try { resultParsed = JSON.parse(tc.result); } catch { resultParsed = tc.result; }
    try { argsParsed = JSON.parse(tc.arguments); } catch { argsParsed = tc.arguments; }

    div.innerHTML = `
        <div class="tool-call-header">
            <span class="tool-icon">🔧</span>
            <span class="tool-name">${Utils.escapeHtml(tc.name)}</span>
            <span class="tool-status">✓</span>
        </div>
        <div class="tool-call-body">
            <div class="tool-section">
                <div class="tool-section-title">Arguments</div>
                <div class="tool-section-content">${Utils.escapeHtml(JSON.stringify(argsParsed, null, 2))}</div>
            </div>
            <div class="tool-section">
                <div class="tool-section-title">Résultat</div>
                <div class="tool-section-content">${Utils.escapeHtml(JSON.stringify(resultParsed, null, 2))}</div>
            </div>
        </div>
    `;
    return div;
}

function newChat() {
    ConversationManager.clear();
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h1>🤖 Copilot Chat</h1>
            <p>Posez-moi une question ou commencez une conversation.</p>
        </div>
    `;
    updateConversationsList();
}

function loadConversation(id) {
    const conv = ConversationManager.setCurrent(id);
    if (!conv) return;

    if (conv.model && modelSelect.querySelector(`option[value="${conv.model}"]`)) {
        modelSelect.value = conv.model;
    }

    messagesContainer.innerHTML = '';
    ConversationManager.messages.forEach(msg => renderMessage(msg));
    updateConversationsList();
}

function deleteConversation(id) {
    if (!confirm('Supprimer cette conversation ?')) return;
    ConversationManager.delete(id);
    if (!ConversationManager.current) {
        newChat();
    }
    updateConversationsList();
}

function updateConversationsList() {
    conversationsContainer.innerHTML = ConversationManager.conversations.map(conv => `
        <div class="conversation-item ${ConversationManager.current?.id === conv.id ? 'active' : ''}" 
             onclick="loadConversation(${conv.id})">
            <span class="conv-title">${Utils.escapeHtml(conv.title)}</span>
            <button class="delete-conv-btn" onclick="event.stopPropagation(); deleteConversation(${conv.id})">×</button>
        </div>
    `).join('');
}
