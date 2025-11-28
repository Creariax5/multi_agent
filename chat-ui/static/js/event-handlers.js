/**
 * Event Handlers - Process SSE events and update UI
 */
const EventHandlers = {
    eventsContainer: null,
    messagesContainer: null,
    responseDiv: null,
    assistantDiv: null,
    messageEvents: [],
    currentContent: '',
    fullContent: '',
    toolCallsExecuted: [],
    currentModel: null,

    init(eventsContainer, messagesContainer, responseDiv, assistantDiv) {
        this.eventsContainer = eventsContainer;
        this.messagesContainer = messagesContainer;
        this.responseDiv = responseDiv;
        this.assistantDiv = assistantDiv;
        this.messageEvents = [];
        this.currentContent = '';
        this.fullContent = '';
        this.toolCallsExecuted = [];
        this.currentModel = null;
    },

    handle(event) {
        const type = event.type;
        
        if (type === 'model_info') {
            this.handleModelInfo(event);
        } else if (type === 'thinking' || type === 'thinking_delta') {
            this.handleThinking(event);
        } else if (type === 'artifact') {
            this.handleArtifact(event);
        } else if (type === 'artifact_edit') {
            this.handleArtifactEdit(event);
        } else if (type === 'batch_artifact_edit') {
            this.handleBatchArtifactEdit(event);
        } else if (type === 'get_artifact') {
            this.handleGetArtifact(event);
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
        
        // Create new artifact
        const artifactId = ArtifactManager.create(event.title, event.content, event.artifact_type || 'html');

        // Save for history
        this.messageEvents.push({
            type: 'artifact',
            title: event.title,
            content: event.content,
            artifact_type: event.artifact_type,
            artifactId: artifactId
        });

        // Add indicator in chat
        const indicator = this.createArtifactIndicator(event.title, artifactId, event.content, event.artifact_type);
        this.eventsContainer.appendChild(indicator);
        this.scrollToBottom();
    },

    handleArtifactEdit(event) {
        console.log('HANDLING ARTIFACT EDIT:', event.description);
        
        // Apply the edit (creates a new version) - now returns object with success/error
        const result = ArtifactManager.applyEdit(
            event.selector,
            event.operation,
            event.content,
            event.attribute
        );
        
        // Get current version number
        const versionNum = ArtifactManager.getCurrentVersion();

        // Save for history
        this.messageEvents.push({
            type: 'artifact_edit',
            selector: event.selector,
            operation: event.operation,
            content: event.content,
            attribute: event.attribute,
            description: event.description,
            success: result.success,
            error: result.error,
            version: versionNum
        });

        // Add edit indicator in chat
        const indicator = this.createEditIndicator(event, versionNum, result);
        this.eventsContainer.appendChild(indicator);
        this.scrollToBottom();
    },

    handleBatchArtifactEdit(event) {
        console.log('HANDLING BATCH EDIT:', event.description, event.operations?.length, 'ops');
        
        const result = ArtifactManager.applyBatchEdit(event.operations, event.dry_run);
        const versionNum = ArtifactManager.getCurrentVersion();

        // Save for history
        this.messageEvents.push({
            type: 'batch_artifact_edit',
            description: event.description,
            operations: event.operations,
            result: result,
            version: versionNum
        });

        // Add batch indicator in chat
        const indicator = this.createBatchEditIndicator(event, result, versionNum);
        this.eventsContainer.appendChild(indicator);
        this.scrollToBottom();
    },

    handleGetArtifact(event) {
        console.log('HANDLING GET ARTIFACT:', event.selector || 'full');
        
        const result = ArtifactManager.getContent(event.selector, event.include_styles);
        
        // Log the structure for debugging
        if (result.success) {
            console.log('Artifact structure:', JSON.stringify(result.structure || result, null, 2));
        }
        
        // This would need backend integration to return to LLM
        // For now, just log it
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
        // Unescape JSON string escapes
        const unescaped = content
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\');
        
        this.fullContent += unescaped;
        this.currentContent += unescaped;
        this.responseDiv.innerHTML = marked.parse(this.currentContent) + '<span class="streaming-cursor">▊</span>';
        this.scrollToBottom();
    },

    handleHistoryUpdate(event) {
        // Handle conversation summarization
        console.log('History update received');
    },

    handleModelInfo(event) {
        this.currentModel = event.model;
        // Update avatar tooltip
        if (this.assistantDiv) {
            const avatar = this.assistantDiv.querySelector('.message-avatar');
            if (avatar) {
                avatar.title = event.model;
                avatar.dataset.model = event.model;
            }
        }
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

    createArtifactIndicator(title, artifactId, content, type) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator';
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">📄</span>
                <span class="artifact-name">${Utils.escapeHtml(title)}</span>
                <span class="artifact-version">V1</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        div.onclick = () => {
            // Restore artifact if it was deleted
            if (!ArtifactManager.artifacts[artifactId]) {
                ArtifactManager.artifacts[artifactId] = {
                    title: title,
                    type: type || 'html',
                    versions: [{ content: content, timestamp: Date.now() }]
                };
                ArtifactManager.save();
            }
            ArtifactManager.select(artifactId);
        };
        return div;
    },

    createEditIndicator(event, versionNum, result = { success: true }) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator artifact-edit' + (result.success ? '' : ' edit-failed');
        const opLabels = {
            'replace': '✏️',
            'insert_after': '➕',
            'insert_before': '➕',
            'delete': '🗑️',
            'set_style': '🎨',
            'set_attribute': '⚙️',
            'append': '➕',
            'prepend': '➕',
            'replace_outer': '🔄',
            'wrap': '📦',
            'unwrap': '📤',
            'clear': '🧹'
        };
        const icon = opLabels[event.operation] || '✏️';
        const statusIcon = result.success ? '' : ' ⚠️';
        const errorText = result.error ? ` <span class="edit-error">(${result.error})</span>` : '';
        
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">${icon}${statusIcon}</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}${errorText}</span>
                <span class="artifact-version">V${versionNum}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        const targetVersion = versionNum - 1;
        div.onclick = () => {
            ArtifactManager.selectVersion(targetVersion);
            ArtifactManager.open();
        };
        return div;
    },

    createBatchEditIndicator(event, result, versionNum) {
        const div = document.createElement('div');
        const allSuccess = result.applied === result.total;
        div.className = 'artifact-indicator artifact-batch-edit' + (allSuccess ? '' : ' partial-success');
        
        const statusText = result.dryRun 
            ? `🔍 Dry run: ${result.results.length} ops validated`
            : `${result.applied}/${result.total} ops applied`;
        
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">📦</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}</span>
                <span class="artifact-batch-status">${statusText}</span>
                <span class="artifact-version">V${versionNum}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        
        const targetVersion = versionNum - 1;
        div.onclick = () => {
            ArtifactManager.selectVersion(targetVersion);
            ArtifactManager.open();
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
