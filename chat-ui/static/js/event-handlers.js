/**
 * Event Handlers - Process SSE events and update UI
 */
const EventHandlers = {
    eventsContainer: null,
    messagesContainer: null,
    responseDiv: null,
    messageEvents: [],
    currentContent: '',
    fullContent: '',
    toolCallsExecuted: [],

    init(eventsContainer, messagesContainer, responseDiv) {
        this.eventsContainer = eventsContainer;
        this.messagesContainer = messagesContainer;
        this.responseDiv = responseDiv;
        this.messageEvents = [];
        this.currentContent = '';
        this.fullContent = '';
        this.toolCallsExecuted = [];
    },

    handle(event) {
        const type = event.type;
        
        if (type === 'thinking' || type === 'thinking_delta') {
            this.handleThinking(event);
        } else if (type === 'artifact') {
            this.handleArtifact(event);
        } else if (type === 'artifact_edit') {
            this.handleArtifactEdit(event);
        } else if (type === 'tool_call') {
            this.handleToolCall(event);
        } else if (event.choices?.[0]?.delta?.content) {
            this.handleTextDelta(event.choices[0].delta.content);
        } else if (type === 'history_update') {
            this.handleHistoryUpdate(event);
        }
    },

    handleThinking(event) {
        const isDelta = event.type === 'thinking_delta';
        
        // Flush text before thinking
        this.flushTextContent();

        let thinkDiv = this.eventsContainer.lastElementChild;
        
        if (thinkDiv?.classList.contains('thinking-block')) {
            const contentDiv = thinkDiv.querySelector('.thinking-content');
            if (isDelta) {
                contentDiv.textContent += event.content;
            } else {
                contentDiv.innerHTML = marked.parse(event.content);
                this.messageEvents.push({ type: 'thinking', content: event.content });
            }
        } else {
            thinkDiv = this.createThinkingBlock();
            this.eventsContainer.appendChild(thinkDiv);
            
            const contentDiv = thinkDiv.querySelector('.thinking-content');
            contentDiv.textContent = event.content;
            
            if (!isDelta) {
                this.messageEvents.push({ type: 'thinking', content: event.content });
            }
        }
        this.scrollToBottom();
    },

    handleArtifact(event) {
        console.log('HANDLING ARTIFACT:', event.title);
        
        const artifactId = ArtifactManager.generateId();
        ArtifactManager.save(artifactId, {
            title: event.title,
            content: event.content,
            artifact_type: event.artifact_type
        });

        // Render immediately
        ArtifactManager.render(event.title, event.content, event.artifact_type);

        // Save for history
        this.messageEvents.push({
            type: 'artifact',
            title: event.title,
            content: event.content,
            artifact_type: event.artifact_type,
            artifactId: artifactId
        });

        // Add indicator in chat
        const indicator = this.createArtifactIndicator(event.title, artifactId);
        this.eventsContainer.appendChild(indicator);
        this.scrollToBottom();
    },

    handleArtifactEdit(event) {
        console.log('HANDLING ARTIFACT EDIT:', event.description);
        
        // Apply the edit to the current artifact
        const success = ArtifactManager.applyEdit(
            event.selector,
            event.operation,
            event.content,
            event.attribute
        );

        // Save for history
        this.messageEvents.push({
            type: 'artifact_edit',
            selector: event.selector,
            operation: event.operation,
            content: event.content,
            attribute: event.attribute,
            description: event.description,
            success: success
        });

        // Add edit indicator in chat
        const indicator = this.createEditIndicator(event);
        this.eventsContainer.appendChild(indicator);
        this.scrollToBottom();
    },

    handleToolCall(event) {
        const tc = event.tool_call;
        this.toolCallsExecuted.push(tc);
        this.flushTextContent();

        const toolDiv = this.createToolCallElement(tc);
        this.eventsContainer.appendChild(toolDiv);
        this.messageEvents.push({ type: 'tool_call', tool_call: tc });
        this.scrollToBottom();
    },

    handleTextDelta(content) {
        this.fullContent += content;
        this.currentContent += content;
        this.responseDiv.innerHTML = marked.parse(this.currentContent) + '<span class="streaming-cursor">▊</span>';
        this.scrollToBottom();
    },

    handleHistoryUpdate(event) {
        // Handle conversation summarization
        console.log('History update received');
    },

    flushTextContent() {
        if (this.currentContent && !this.eventsContainer.lastElementChild?.classList.contains('thinking-block')) {
            const textDiv = document.createElement('div');
            textDiv.className = 'response-text-block';
            textDiv.innerHTML = marked.parse(this.currentContent);
            this.eventsContainer.appendChild(textDiv);
            this.messageEvents.push({ type: 'text', content: this.currentContent });
            this.currentContent = '';
        }
    },

    finalize() {
        if (this.currentContent) {
            const textDiv = document.createElement('div');
            textDiv.className = 'response-text-block';
            textDiv.innerHTML = marked.parse(this.currentContent);
            this.eventsContainer.appendChild(textDiv);
            this.messageEvents.push({ type: 'text', content: this.currentContent });
        }

        if (this.eventsContainer.childElementCount > 0) {
            this.responseDiv.remove();
        } else if (!this.fullContent) {
            this.responseDiv.innerHTML = '<span style="color: #ff6b6b;">Aucune réponse reçue</span>';
        }

        return {
            content: this.fullContent,
            events: this.messageEvents,
            toolCalls: this.toolCallsExecuted
        };
    },

    // UI Helper Methods
    createThinkingBlock() {
        const div = document.createElement('div');
        div.className = 'thinking-block';
        div.innerHTML = `
            <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                <span class="thinking-icon">💭</span>
                <span class="thinking-label">Réflexion</span>
                <span class="thinking-toggle">▼</span>
            </div>
            <div class="thinking-content"></div>
        `;
        return div;
    },

    createArtifactIndicator(title, artifactId) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator';
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">📄</span>
                <span class="artifact-name">${Utils.escapeHtml(title)}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        div.onclick = () => {
            const art = ArtifactManager.get(artifactId);
            if (art) ArtifactManager.render(art.title, art.content, art.artifact_type);
        };
        return div;
    },

    createEditIndicator(event) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator artifact-edit';
        const opLabels = {
            'replace': '✏️',
            'insert_after': '➕',
            'insert_before': '➕',
            'delete': '🗑️',
            'set_style': '🎨',
            'set_attribute': '⚙️',
            'append': '➕',
            'prepend': '➕'
        };
        const icon = opLabels[event.operation] || '✏️';
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">${icon}</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}</span>
                <span class="artifact-selector">${Utils.escapeHtml(event.selector)}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        // Clicking opens the artifact panel
        div.onclick = () => {
            if (!ArtifactManager.panel.classList.contains('open')) {
                ArtifactManager.panel.classList.add('open');
            }
        };
        return div;
    },

    createToolCallElement(tc) {
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
    },

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
};
