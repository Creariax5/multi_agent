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
const useToolsCheckbox = document.getElementById('use-tools');
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
    
    // Restore tools preference
    const savedTools = localStorage.getItem('useTools');
    if (savedTools !== null) {
        useToolsCheckbox.checked = savedTools === 'true';
    }
    
    // Save model selection
    modelSelect.addEventListener('change', () => {
        localStorage.setItem('selectedModel', modelSelect.value);
        if (currentConversation) {
            currentConversation.model = modelSelect.value;
            saveConversations();
        }
    });
    
    // Save tools preference
    useToolsCheckbox.addEventListener('change', () => {
        localStorage.setItem('useTools', useToolsCheckbox.checked);
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
    
    // Create assistant message container for streaming
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
    let fullContent = '';
    let toolCallsExecuted = [];
    let currentContent = '';  // Track content for interleaved display
    let messageEvents = [];   // Track sequence of events for saving
    let currentTextBuffer = ''; // Buffer for text chunks to create text events

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: messages,
                model: modelSelect.value,
                use_tools: useToolsCheckbox.checked
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';  // Buffer for incomplete SSE lines

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            
            // Keep the last potentially incomplete line in buffer
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;
                    if (!data) continue;
                    
                    try {
                        const parsed = JSON.parse(data);
                        
                        // === THINKING EVENT (Final or Delta) ===
                        if ((parsed.type === 'thinking' || parsed.type === 'thinking_delta') && parsed.content) {
                            const isDelta = parsed.type === 'thinking_delta';
                            
                            // Flush current text content before thinking (only if starting new block)
                            if (currentContent && !eventsContainer.lastElementChild?.classList.contains('thinking-block')) {
                                const textDiv = document.createElement('div');
                                textDiv.className = 'response-text-block';
                                textDiv.innerHTML = marked.parse(currentContent);
                                eventsContainer.appendChild(textDiv);
                                
                                // Save text event
                                messageEvents.push({ type: 'text', content: currentContent });
                                currentContent = '';
                            }
                            
                            let thinkDiv = eventsContainer.lastElementChild;
                            
                            // Reuse if it's a thinking block
                            if (thinkDiv && thinkDiv.classList.contains('thinking-block')) {
                                const contentDiv = thinkDiv.querySelector('.thinking-content');
                                if (isDelta) {
                                    // Append raw text
                                    contentDiv.textContent += parsed.content;
                                } else {
                                    // Final event: Replace content with proper Markdown
                                    contentDiv.innerHTML = marked.parse(parsed.content);
                                    
                                    // Save thinking event (only final)
                                    messageEvents.push({ type: 'thinking', content: parsed.content });
                                }
                            } else {
                                // Create new thinking block
                                thinkDiv = document.createElement('div');
                                thinkDiv.className = 'thinking-block';
                                thinkDiv.innerHTML = `
                                    <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                                        <span class="thinking-icon">💭</span>
                                        <span class="thinking-label">Réflexion</span>
                                        <span class="thinking-toggle">▼</span>
                                    </div>
                                    <div class="thinking-content"></div>
                                `;
                                eventsContainer.appendChild(thinkDiv);
                                
                                const contentDiv = thinkDiv.querySelector('.thinking-content');
                                if (isDelta) {
                                    contentDiv.textContent = parsed.content;
                                } else {
                                    contentDiv.innerHTML = marked.parse(parsed.content);
                                    // Save thinking event
                                    messageEvents.push({ type: 'thinking', content: parsed.content });
                                }
                            }
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                        
                        // === TOOL CALL EVENT ===
                        if (parsed.type === 'tool_call' && parsed.tool_call) {
                            const tc = parsed.tool_call;
                            toolCallsExecuted.push(tc);
                            
                            // Flush current text content before tool
                            if (currentContent) {
                                const textDiv = document.createElement('div');
                                textDiv.className = 'response-text-block';
                                textDiv.innerHTML = marked.parse(currentContent);
                                eventsContainer.appendChild(textDiv);
                                
                                // Save text event
                                messageEvents.push({ type: 'text', content: currentContent });
                                currentContent = '';
                            }
                            
                            // Create compact tool call element
                            const toolDiv = document.createElement('div');
                            toolDiv.className = 'tool-call';
                            toolDiv.onclick = function() { this.classList.toggle('expanded'); };
                            
                            let resultParsed, argsParsed;
                            try { resultParsed = JSON.parse(tc.result); } catch { resultParsed = tc.result; }
                            try { argsParsed = JSON.parse(tc.arguments); } catch { argsParsed = tc.arguments; }
                            
                            toolDiv.innerHTML = `
                                <div class="tool-call-header">
                                    <span class="tool-icon">🔧</span>
                                    <span class="tool-name">${escapeHtml(tc.name)}</span>
                                    <span class="tool-status">✓</span>
                                </div>
                                <div class="tool-call-body">
                                    <div class="tool-section">
                                        <div class="tool-section-title">Arguments</div>
                                        <div class="tool-section-content">${escapeHtml(JSON.stringify(argsParsed, null, 2))}</div>
                                    </div>
                                    <div class="tool-section">
                                        <div class="tool-section-title">Résultat</div>
                                        <div class="tool-section-content">${escapeHtml(JSON.stringify(resultParsed, null, 2))}</div>
                                    </div>
                                </div>
                            `;
                            eventsContainer.appendChild(toolDiv);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;

                            // Save tool event
                            messageEvents.push({ type: 'tool_call', tool_call: tc });
                        }
                        
                        // === HISTORY UPDATE EVENT ===
                        if (parsed.type === 'history_update' && parsed.messages) {
                            // The backend has summarized the conversation.
                            // We need to update our local state to match, otherwise we'll keep sending the old full history.
                            
                            // Filter out system messages for display/storage (usually we only keep user/assistant)
                            // But here the summary is likely a user message or similar.
                            const newMessages = parsed.messages.filter(m => m.role !== 'system');
                            
                            // Update local state
                            messages = newMessages;
                            
                            // Clear UI and re-render
                            messagesContainer.innerHTML = '';
                            
                            // Add a visual indicator
                            const separator = document.createElement('div');
                            separator.className = 'message system';
                            separator.innerHTML = '<div class="message-content" style="text-align: center; color: #888;">--- Conversation Résumée ---</div>';
                            messagesContainer.appendChild(separator);
                            
                            // Render new messages
                            messages.forEach(msg => renderMessage(msg));
                            
                            // Re-append the current assistant response container (since we just wiped the UI)
                            messagesContainer.appendChild(assistantDiv);
                            
                            // Save immediately
                            saveConversation();
                        }

                        // === TEXT CONTENT EVENT ===
                        // Only process content from regular chat chunks (not thinking or tool_call events)
                        if (parsed.choices && parsed.choices[0]?.delta?.content) {
                            const textContent = parsed.choices[0].delta.content;
                            fullContent += textContent;
                            currentContent += textContent;
                            responseDiv.innerHTML = marked.parse(currentContent) + '<span class="streaming-cursor">▊</span>';
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                        
                        // === ERROR EVENT ===
                        if (parsed.error) {
                            responseDiv.innerHTML = `<span style="color: #ff6b6b;">${escapeHtml(parsed.error)}</span>`;
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }
        }

        // Finalize: add remaining content
        if (currentContent) {
            const textDiv = document.createElement('div');
            textDiv.className = 'response-text-block';
            textDiv.innerHTML = marked.parse(currentContent);
            eventsContainer.appendChild(textDiv);
            
            // Save final text event
            messageEvents.push({ type: 'text', content: currentContent });
        }
        
        // Remove streaming cursor
        if (eventsContainer.childElementCount > 0) {
            responseDiv.remove();
        } else if (!fullContent) {
            responseDiv.innerHTML = '<span style="color: #ff6b6b;">Aucune réponse reçue</span>';
        }

        if (fullContent || messageEvents.length > 0) {
            const assistantMessage = { 
                role: 'assistant', 
                content: fullContent,
                tool_calls: toolCallsExecuted.length > 0 ? toolCallsExecuted : undefined,
                events: messageEvents.length > 0 ? messageEvents : undefined
            };
            messages.push(assistantMessage);
            saveConversation();
        }

    } catch (error) {
        responseDiv.innerHTML = `<span style="color: #ff6b6b;">Erreur: ${escapeHtml(error.message)}</span>`;
    }

    isLoading = false;
    sendBtn.disabled = false;
    messageInput.focus();
}

// Render tool calls
function renderToolCalls(container, toolCalls) {
    container.innerHTML = toolCalls.map((tc, i) => {
        let resultParsed;
        try {
            resultParsed = typeof tc.result === 'string' ? JSON.parse(tc.result) : tc.result;
        } catch {
            resultParsed = tc.result;
        }
        
        let argsParsed;
        try {
            argsParsed = typeof tc.arguments === 'string' ? JSON.parse(tc.arguments) : tc.arguments;
        } catch {
            argsParsed = tc.arguments;
        }
        
        return `
            <div class="tool-call" onclick="this.classList.toggle('expanded')">
                <div class="tool-call-header">
                    <span class="tool-icon">🔧</span>
                    <span class="tool-name">${escapeHtml(tc.name)}</span>
                    <span class="tool-status">✓ Exécuté</span>
                </div>
                <div class="tool-call-body">
                    <div class="tool-section">
                        <div class="tool-section-title">Arguments</div>
                        <div class="tool-section-content">${escapeHtml(JSON.stringify(argsParsed, null, 2))}</div>
                    </div>
                    <div class="tool-section">
                        <div class="tool-section-title">Résultat</div>
                        <div class="tool-section-content">${escapeHtml(JSON.stringify(resultParsed, null, 2))}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Render message
function renderMessage(message) {
    const div = document.createElement('div');
    div.className = `message ${message.role}`;
    
    const avatar = message.role === 'user' ? '👤' : '🤖';
    
    // If we have structured events (new format), render them in order
    if (message.role === 'assistant' && message.events && message.events.length > 0) {
        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="events-container"></div>
            </div>
        `;
        
        const eventsContainer = div.querySelector('.events-container');
        
        message.events.forEach(event => {
            if (event.type === 'thinking') {
                const thinkDiv = document.createElement('div');
                thinkDiv.className = 'thinking-block';
                thinkDiv.innerHTML = `
                    <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                        <span class="thinking-icon">💭</span>
                        <span class="thinking-label">Réflexion</span>
                        <span class="thinking-toggle">▼</span>
                    </div>
                    <div class="thinking-content">${marked.parse(event.content)}</div>
                `;
                eventsContainer.appendChild(thinkDiv);
            } else if (event.type === 'tool_call') {
                const tc = event.tool_call;
                let resultParsed, argsParsed;
                try { resultParsed = typeof tc.result === 'string' ? JSON.parse(tc.result) : tc.result; } catch { resultParsed = tc.result; }
                try { argsParsed = typeof tc.arguments === 'string' ? JSON.parse(tc.arguments) : tc.arguments; } catch { argsParsed = tc.arguments; }
                
                const toolDiv = document.createElement('div');
                toolDiv.className = 'tool-call';
                toolDiv.onclick = function() { this.classList.toggle('expanded'); };
                toolDiv.innerHTML = `
                    <div class="tool-call-header">
                        <span class="tool-icon">🔧</span>
                        <span class="tool-name">${escapeHtml(tc.name)}</span>
                        <span class="tool-status">✓ Exécuté</span>
                    </div>
                    <div class="tool-call-body">
                        <div class="tool-section">
                            <div class="tool-section-title">Arguments</div>
                            <div class="tool-section-content">${escapeHtml(JSON.stringify(argsParsed, null, 2))}</div>
                        </div>
                        <div class="tool-section">
                            <div class="tool-section-title">Résultat</div>
                            <div class="tool-section-content">${escapeHtml(JSON.stringify(resultParsed, null, 2))}</div>
                        </div>
                    </div>
                `;
                eventsContainer.appendChild(toolDiv);
            } else if (event.type === 'text') {
                const textDiv = document.createElement('div');
                textDiv.className = 'response-text-block';
                textDiv.innerHTML = marked.parse(event.content);
                eventsContainer.appendChild(textDiv);
            }
        });
        
    } else {
        // Legacy rendering (or user messages)
        let content = message.content;
        if (message.role === 'assistant') {
            content = marked.parse(content);
        } else {
            content = escapeHtml(content).replace(/\n/g, '<br>');
        }
        
        // Build tool calls HTML if present
        let toolCallsHtml = '';
        if (message.role === 'assistant' && message.tool_calls && message.tool_calls.length > 0) {
            const toolCallsContent = message.tool_calls.map(tc => {
                let resultParsed, argsParsed;
                try {
                    resultParsed = typeof tc.result === 'string' ? JSON.parse(tc.result) : tc.result;
                } catch { resultParsed = tc.result; }
                try {
                    argsParsed = typeof tc.arguments === 'string' ? JSON.parse(tc.arguments) : tc.arguments;
                } catch { argsParsed = tc.arguments; }
                
                return `
                    <div class="tool-call" onclick="this.classList.toggle('expanded')">
                        <div class="tool-call-header">
                            <span class="tool-icon">🔧</span>
                            <span class="tool-name">${escapeHtml(tc.name || 'unknown')}</span>
                            <span class="tool-status">✓ Exécuté</span>
                        </div>
                        <div class="tool-call-body">
                            <div class="tool-section">
                                <div class="tool-section-title">Arguments</div>
                                <div class="tool-section-content">${escapeHtml(JSON.stringify(argsParsed, null, 2))}</div>
                            </div>
                            <div class="tool-section">
                                <div class="tool-section-title">Résultat</div>
                                <div class="tool-section-content">${escapeHtml(JSON.stringify(resultParsed, null, 2))}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            toolCallsHtml = `<div class="tool-calls-container">${toolCallsContent}</div>`;
        }
        
        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                ${toolCallsHtml}
                <div class="response-text">${content}</div>
            </div>
        `;
    }
    
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
