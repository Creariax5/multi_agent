/**
 * UI Builders - DOM element creation for chat events
 * Pure functions that create and return DOM elements
 */
const UIBuilders = {

    // ==================== THINKING ====================
    
    thinkingBlock() {
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

    // ==================== ARTIFACTS ====================

    artifactIndicator(title, artifactId, content, type) {
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
            if (!ArtifactManager.artifacts[artifactId]) {
                ArtifactManager.artifacts[artifactId] = {
                    title,
                    type: type || 'html',
                    versions: [{ content, timestamp: Date.now() }]
                };
                ArtifactManager.save();
            }
            ArtifactManager.select(artifactId);
        };
        return div;
    },

    editIndicator(event, versionNum, result = { success: true }, artifactInfo = null) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator artifact-edit' + (result.success ? '' : ' edit-failed');
        
        const icons = {
            replace: '✏️', insert_after: '➕', insert_before: '➕',
            delete: '🗑️', set_style: '🎨', set_attribute: '⚙️',
            append: '➕', prepend: '➕', replace_outer: '🔄',
            wrap: '📦', unwrap: '📤', clear: '🧹'
        };
        const icon = icons[event.operation] || '✏️';
        const errorText = result.error ? ` <span class="edit-error">(${result.error})</span>` : '';
        
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">${icon}${result.success ? '' : ' ⚠️'}</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}${errorText}</span>
                <span class="artifact-version">V${versionNum}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        
        div.onclick = () => this._restoreAndShow(artifactInfo, versionNum - 1);
        return div;
    },

    batchEditIndicator(event, result, versionNum, artifactInfo = null) {
        const div = document.createElement('div');
        const allSuccess = result.applied === result.total;
        div.className = 'artifact-indicator artifact-batch-edit' + (allSuccess ? '' : ' partial-success');
        
        const statusText = result.dryRun 
            ? `🔍 Dry run: ${result.results.length} ops`
            : `${result.applied}/${result.total} ops`;
        
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">📦</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}</span>
                <span class="artifact-batch-status">${statusText}</span>
                <span class="artifact-version">V${versionNum}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        
        div.onclick = () => this._restoreAndShow(artifactInfo, versionNum - 1);
        return div;
    },

    // Simple replace indicator (cleaner, more reliable)
    replaceIndicator(event, versionNum, result = { success: true }, artifactInfo = null) {
        const div = document.createElement('div');
        div.className = 'artifact-indicator artifact-replace' + (result.success ? '' : ' edit-failed');
        
        const icon = result.success ? '🔄' : '⚠️';
        const errorText = result.error ? ` <span class="edit-error">(${result.error})</span>` : '';
        
        div.innerHTML = `
            <div class="artifact-indicator-header">
                <span class="artifact-icon">${icon}</span>
                <span class="artifact-name">${Utils.escapeHtml(event.description)}${errorText}</span>
                <span class="artifact-version">V${versionNum}</span>
                <span class="artifact-action">Voir →</span>
            </div>
        `;
        
        div.onclick = () => this._restoreAndShow(artifactInfo, versionNum - 1);
        return div;
    },

    _restoreAndShow(artifactInfo, targetVersion) {
        if (artifactInfo && !ArtifactManager.artifacts[artifactInfo.artifactId]) {
            ArtifactManager.artifacts[artifactInfo.artifactId] = {
                title: artifactInfo.title,
                type: artifactInfo.type,
                versions: artifactInfo.allVersions.length > 0 
                    ? artifactInfo.allVersions 
                    : [{ content: artifactInfo.versionContent, timestamp: Date.now() }]
            };
            ArtifactManager.activeId = artifactInfo.artifactId;
            ArtifactManager.save();
        }
        ArtifactManager.selectVersion(targetVersion);
        ArtifactManager.open();
    },

    // ==================== TOOL CALLS ====================

    toolCall(tc) {
        const div = document.createElement('div');
        div.className = 'tool-call';
        div.onclick = function() { this.classList.toggle('expanded'); };

        let args, result;
        try { args = JSON.parse(tc.arguments); } catch { args = tc.arguments; }
        try { result = JSON.parse(tc.result); } catch { result = tc.result; }

        div.innerHTML = `
            <div class="tool-call-header">
                <span class="tool-icon">🔧</span>
                <span class="tool-name">${Utils.escapeHtml(tc.name)}</span>
                <span class="tool-status">✓</span>
            </div>
            <div class="tool-call-body">
                <div class="tool-section">
                    <div class="tool-section-title">Arguments</div>
                    <div class="tool-section-content">${Utils.escapeHtml(JSON.stringify(args, null, 2))}</div>
                </div>
                <div class="tool-section">
                    <div class="tool-section-title">Résultat</div>
                    <div class="tool-section-content">${Utils.escapeHtml(JSON.stringify(result, null, 2))}</div>
                </div>
            </div>
        `;
        return div;
    },

    // ==================== TEXT ====================

    textBlock(content) {
        const div = document.createElement('div');
        div.className = 'response-text-block';
        div.innerHTML = marked.parse(content);
        return div;
    }
};
