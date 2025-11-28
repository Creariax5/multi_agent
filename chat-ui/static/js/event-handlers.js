/**
 * Event Handlers - Process SSE events and update UI
 * Lightweight dispatcher + business logic
 */
const EventHandlers = {
    // DOM refs
    container: null,
    messages: null,
    responseDiv: null,
    
    // State
    events: [],
    content: '',
    fullContent: '',
    toolCalls: [],
    model: null,
    pendingEdits: [],

    init(container, messages, responseDiv, assistantDiv) {
        Object.assign(this, {
            container, messages, responseDiv,
            events: [], content: '', fullContent: '',
            toolCalls: [], model: null, pendingEdits: []
        });
        this.assistantDiv = assistantDiv;
    },

    // ==================== DISPATCHER ====================

    handle(event) {
        const handlers = {
            'model_info': () => this.onModelInfo(event),
            'thinking': () => this.onThinking(event),
            'thinking_delta': () => this.onThinking(event),
            'artifact': () => this.onArtifact(event),
            'artifact_edit': () => this.onArtifactEdit(event),
            'replace_in_artifact': () => this.onReplaceInArtifact(event),
            'batch_artifact_edit': () => this.onBatchEdit(event),
            'get_artifact': () => this.onGetArtifact(event),
            'tool_call': () => this.onToolCall(event)
        };

        if (handlers[event.type]) {
            handlers[event.type]();
        } else if (event.choices?.[0]?.delta?.content) {
            this.onTextDelta(event.choices[0].delta.content);
        }
    },

    // ==================== HANDLERS ====================

    onModelInfo(e) {
        this.model = e.model;
        const avatar = this.assistantDiv?.querySelector('.message-avatar');
        if (avatar) avatar.title = e.model;
    },

    onThinking(e) {
        const isDelta = e.type === 'thinking_delta';
        this.flushText();

        let block = this.container.lastElementChild;
        if (!block?.classList.contains('thinking-block')) {
            block = UIBuilders.thinkingBlock();
            this.container.appendChild(block);
        }

        const content = block.querySelector('.thinking-content');
        if (isDelta) {
            content.textContent += e.content;
        } else {
            content.innerHTML = marked.parse(e.content);
            this.events.push({ type: 'thinking', content: e.content });
        }
        this.scroll();
    },

    onArtifact(e) {
        const id = ArtifactManager.create(e.title, e.content, e.artifact_type || 'html');
        
        this.events.push({
            type: 'artifact', title: e.title, content: e.content,
            artifact_type: e.artifact_type, artifactId: id
        });

        this.container.appendChild(UIBuilders.artifactIndicator(e.title, id, e.content, e.artifact_type));
        this.scroll();
        this.processPendingEdits();
    },

    onArtifactEdit(e) {
        if (!this.isIframeReady()) {
            this.pendingEdits.push({ type: 'edit', event: e });
            this.processPendingEdits();
            return;
        }
        this.executeEdit(e);
    },

    executeEdit(e) {
        const result = ArtifactManager.applyEdit(e.selector, e.operation, e.content, e.attribute);
        const info = this.captureArtifactInfo();
        
        this.events.push({
            type: 'artifact_edit', ...e,
            success: result.success, error: result.error,
            version: info.version, artifactId: info.id
        });

        this.container.appendChild(UIBuilders.editIndicator(e, info.version, result, info));
        this.scroll();
    },

    // Simple string replacement (like Copilot's replace_string_in_file)
    onReplaceInArtifact(e) {
        console.log('REPLACE IN ARTIFACT:', e.description);
        console.log('  old_string length:', e.old_string?.length);
        console.log('  new_string length:', e.new_string?.length);
        
        const result = ArtifactManager.replaceString(e.old_string, e.new_string);
        console.log('  result:', result);
        
        const info = this.captureArtifactInfo();
        
        this.events.push({
            type: 'replace_in_artifact',
            description: e.description,
            success: result.success,
            error: result.error,
            version: info.version,
            artifactId: info.id
        });

        this.container.appendChild(UIBuilders.replaceIndicator(e, info.version, result, info));
        this.scroll();
    },

    onBatchEdit(e) {
        if (!this.isIframeReady()) {
            this.pendingEdits.push({ type: 'batch', event: e });
            this.processPendingEdits();
            return;
        }
        this.executeBatchEdit(e);
    },

    executeBatchEdit(e) {
        const result = ArtifactManager.applyBatchEdit(e.operations, e.dry_run);
        const info = this.captureArtifactInfo();

        this.events.push({
            type: 'batch_artifact_edit', description: e.description,
            operations: e.operations, result, version: info.version, artifactId: info.id
        });

        this.container.appendChild(UIBuilders.batchEditIndicator(e, result, info.version, info));
        this.scroll();
    },

    onGetArtifact(e) {
        const result = ArtifactManager.getContent(e.selector, e.include_styles);
        if (result.success) console.log('Artifact structure:', result.structure || result);
    },

    onToolCall(e) {
        this.toolCalls.push(e.tool_call);
        this.flushText();
        this.container.appendChild(UIBuilders.toolCall(e.tool_call));
        this.events.push({ type: 'tool_call', tool_call: e.tool_call });
        this.scroll();
    },

    onTextDelta(text) {
        const clean = text.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
        this.fullContent += clean;
        this.content += clean;
        this.responseDiv.innerHTML = marked.parse(this.content) + '<span class="streaming-cursor">▊</span>';
        this.scroll();
    },

    // ==================== HELPERS ====================

    isIframeReady() {
        const doc = document.getElementById('artifact-iframe')?.contentDocument;
        return doc?.body?.innerHTML?.trim();
    },

    captureArtifactInfo() {
        const art = ArtifactManager.artifacts[ArtifactManager.activeId];
        return {
            artifactId: ArtifactManager.activeId,
            id: ArtifactManager.activeId,
            title: art?.title || 'Artifact',
            type: art?.type || 'html',
            version: ArtifactManager.getCurrentVersion(),
            versionContent: art?.versions[ArtifactManager.getCurrentVersion() - 1]?.content || '',
            allVersions: art ? [...art.versions] : []
        };
    },

    processPendingEdits(retries = 0) {
        if (!this.pendingEdits.length) return;

        if (this.isIframeReady()) {
            const edits = [...this.pendingEdits];
            this.pendingEdits = [];
            edits.forEach(p => p.type === 'edit' ? this.executeEdit(p.event) : this.executeBatchEdit(p.event));
        } else if (retries < 20) {
            setTimeout(() => this.processPendingEdits(retries + 1), 100);
        } else {
            this.pendingEdits.forEach(p => {
                this.container.appendChild(UIBuilders.editIndicator(p.event, 0, { success: false, error: 'Timeout' }));
            });
            this.pendingEdits = [];
        }
    },

    flushText() {
        if (this.content && !this.container.lastElementChild?.classList.contains('thinking-block')) {
            this.container.appendChild(UIBuilders.textBlock(this.content));
            this.events.push({ type: 'text', content: this.content });
            this.content = '';
        }
    },

    scroll() {
        this.messages.scrollTop = this.messages.scrollHeight;
    },

    finalize() {
        if (this.content) {
            this.container.appendChild(UIBuilders.textBlock(this.content));
            this.events.push({ type: 'text', content: this.content });
        }

        if (this.container.childElementCount > 0) {
            this.responseDiv.remove();
        } else if (!this.fullContent) {
            this.responseDiv.innerHTML = '<span style="color: #ff6b6b;">Aucune réponse</span>';
        }

        return { content: this.fullContent, events: this.events, toolCalls: this.toolCalls };
    }
};
