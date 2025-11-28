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
        EventHandlers.init(eventsContainer, messagesContainer, responseDiv, assistantDiv);

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
                model: EventHandlers.model || modelSelect.value,
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
    const modelTitle = message.model ? `title="${message.model}"` : '';

    if (message.role === 'assistant' && message.events?.length > 0) {
        div.innerHTML = `
            <div class="message-avatar" ${modelTitle}>${avatar}</div>
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
            } else if (event.type === 'artifact_edit') {
                container.appendChild(createEditIndicatorForRender(event));
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
            <div class="message-avatar" ${modelTitle}>${avatar}</div>
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
    const block = UIBuilders.thinkingBlock();
    block.querySelector('.thinking-content').innerHTML = marked.parse(content);
    return block;
}

function createArtifactIndicatorForRender(event) {
    return UIBuilders.artifactIndicator(
        event.title, 
        event.artifactId, 
        event.content, 
        event.artifact_type
    );
}

function createEditIndicatorForRender(event) {
    // Build artifactInfo from saved event data
    const artifactInfo = event.artifactId ? {
        artifactId: event.artifactId,
        title: event.title || 'Artifact',
        type: event.artifact_type || 'html',
        versionContent: event.content || '',
        allVersions: []
    } : null;
    
    return UIBuilders.editIndicator(
        event,
        event.version || 1,
        { success: event.success !== false, error: event.error },
        artifactInfo
    );
}

function createToolCallForRender(tc) {
    return UIBuilders.toolCall(tc);
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
