/**
 * Artifact Manager - Multi-artifact system with versioning
 * 
 * Structure:
 * - artifacts: { id: { title, type, versions: [{ content, timestamp }] } }
 * - Each artifact has its own version history
 * - UI shows tabs for switching between artifacts
 */
const ArtifactManager = {
    // State
    artifacts: {},           // All artifacts
    activeId: null,          // Currently displayed artifact
    activeVersion: 0,        // Current version index
    view: 'preview',         // 'preview' or 'code'
    isOpen: false,

    // DOM elements (cached on init)
    els: {},

    init() {
        this.els = {
            panel: document.getElementById('artifact-panel'),
            tabs: document.getElementById('artifact-tabs'),
            title: document.getElementById('artifact-title'),
            versions: document.getElementById('version-selector'),
            content: document.getElementById('artifact-content'),
            viewIcon: document.getElementById('view-icon')
        };
        this.load();
        this.render();
    },

    // ==================== STORAGE ====================
    
    load() {
        try {
            const data = JSON.parse(localStorage.getItem('artifacts') || '{}');
            this.artifacts = data.artifacts || {};
            this.activeId = data.activeId || null;
            this.activeVersion = data.activeVersion || 0;
            this.isOpen = data.isOpen || false;
        } catch (e) {
            console.warn('Failed to load artifacts:', e);
        }
    },

    save() {
        try {
            localStorage.setItem('artifacts', JSON.stringify({
                artifacts: this.artifacts,
                activeId: this.activeId,
                activeVersion: this.activeVersion,
                isOpen: this.isOpen
            }));
        } catch (e) {
            console.warn('Failed to save artifacts:', e);
        }
    },

    // ==================== ARTIFACT CRUD ====================

    create(title, content, type = 'html') {
        const id = 'art_' + Date.now();
        this.artifacts[id] = {
            title,
            type,
            versions: [{ content, timestamp: Date.now() }]
        };
        this.activeId = id;
        this.activeVersion = 0;
        this.isOpen = true;
        this.save();
        this.render();
        return id;
    },

    addVersion(content) {
        const art = this.artifacts[this.activeId];
        if (!art) return;
        
        art.versions.push({ content, timestamp: Date.now() });
        this.activeVersion = art.versions.length - 1;
        this.save();
        this.renderVersions();
    },

    delete(id) {
        delete this.artifacts[id];
        if (this.activeId === id) {
            const ids = Object.keys(this.artifacts);
            this.activeId = ids[0] || null;
            this.activeVersion = 0;
        }
        this.save();
        this.render();
    },

    // ==================== NAVIGATION ====================

    select(id) {
        if (!this.artifacts[id]) return;
        this.activeId = id;
        this.activeVersion = this.artifacts[id].versions.length - 1;
        this.isOpen = true;
        this.save();
        this.render();
    },

    selectVersion(index) {
        const art = this.artifacts[this.activeId];
        if (!art || index < 0 || index >= art.versions.length) return;
        this.activeVersion = index;
        this.save();
        this.renderContent();
    },

    // ==================== EDIT OPERATIONS ====================

    applyEdit(selector, operation, content, attribute) {
        const iframe = document.getElementById('artifact-iframe');
        const doc = iframe?.contentDocument;
        if (!doc) return { success: false, error: 'No iframe document' };

        // Handle pseudo-selectors via style injection
        if (/:(hover|focus|active)|::/.test(selector)) {
            if (operation === 'set_style') {
                this._injectStyle(doc, selector, content);
                this._commitVersion(doc);
                return { success: true };
            }
            return { success: false, error: 'Pseudo-selector only supports set_style' };
        }

        let el;
        try {
            el = doc.querySelector(selector);
        } catch (e) {
            return { success: false, error: `Invalid selector: ${selector}` };
        }

        if (!el && /^body$/i.test(selector)) el = doc.body;
        if (!el) return { success: false, error: `Element not found: ${selector}` };

        const ops = {
            replace: () => el.innerHTML = content,
            insert_after: () => el.insertAdjacentHTML('afterend', content),
            insert_before: () => el.insertAdjacentHTML('beforebegin', content),
            delete: () => el.remove(),
            append: () => el.insertAdjacentHTML('beforeend', content),
            prepend: () => el.insertAdjacentHTML('afterbegin', content),
            set_attribute: () => el.setAttribute(attribute, content),
            set_style: () => {
                content.split(';').forEach(rule => {
                    const [prop, val] = rule.split(':').map(s => s.trim());
                    if (prop && val) el.style[this._camelCase(prop)] = val;
                });
            },
            // NEW OPERATIONS
            replace_outer: () => el.outerHTML = content,
            wrap: () => {
                const wrapper = doc.createElement('div');
                wrapper.innerHTML = content;
                const wrapperEl = wrapper.firstElementChild;
                if (wrapperEl) {
                    el.parentNode.insertBefore(wrapperEl, el);
                    wrapperEl.appendChild(el);
                }
            },
            unwrap: () => {
                const parent = el.parentNode;
                while (el.firstChild) {
                    parent.insertBefore(el.firstChild, el);
                }
                el.remove();
            },
            clear: () => el.innerHTML = ''
        };

        if (!ops[operation]) return { success: false, error: `Unknown operation: ${operation}` };
        
        try {
            ops[operation]();
            this._commitVersion(doc);
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    // Batch edit - apply multiple operations atomically
    applyBatchEdit(operations, dryRun = false) {
        const iframe = document.getElementById('artifact-iframe');
        const doc = iframe?.contentDocument;
        if (!doc) return { success: false, results: [], error: 'No iframe document' };

        const results = [];
        
        // In dry-run mode, we validate but don't apply
        if (dryRun) {
            for (const op of operations) {
                let el;
                try {
                    el = doc.querySelector(op.selector);
                    if (!el && /^body$/i.test(op.selector)) el = doc.body;
                    results.push({
                        selector: op.selector,
                        operation: op.operation,
                        found: !!el,
                        currentContent: el ? el.innerHTML.slice(0, 100) + '...' : null
                    });
                } catch (e) {
                    results.push({ selector: op.selector, error: e.message });
                }
            }
            return { success: true, dryRun: true, results };
        }

        // Apply each operation
        for (const op of operations) {
            const result = this._applyEditNoCommit(doc, op.selector, op.operation, op.content || '', op.attribute || '');
            results.push({ ...op, ...result });
        }

        // Commit once at the end
        this._commitVersion(doc);
        
        const successCount = results.filter(r => r.success).length;
        return { 
            success: successCount > 0, 
            applied: successCount, 
            total: operations.length,
            results 
        };
    },

    // Internal: apply edit without committing version
    _applyEditNoCommit(doc, selector, operation, content, attribute) {
        if (/:(hover|focus|active)|::/.test(selector)) {
            if (operation === 'set_style') {
                this._injectStyle(doc, selector, content);
                return { success: true };
            }
            return { success: false, error: 'Pseudo-selector only supports set_style' };
        }

        let el;
        try {
            el = doc.querySelector(selector);
        } catch (e) {
            return { success: false, error: `Invalid selector` };
        }

        if (!el && /^body$/i.test(selector)) el = doc.body;
        if (!el) return { success: false, error: `Not found` };

        const ops = {
            replace: () => el.innerHTML = content,
            insert_after: () => el.insertAdjacentHTML('afterend', content),
            insert_before: () => el.insertAdjacentHTML('beforebegin', content),
            delete: () => el.remove(),
            append: () => el.insertAdjacentHTML('beforeend', content),
            prepend: () => el.insertAdjacentHTML('afterbegin', content),
            set_attribute: () => el.setAttribute(attribute, content),
            set_style: () => {
                content.split(';').forEach(rule => {
                    const [prop, val] = rule.split(':').map(s => s.trim());
                    if (prop && val) el.style[this._camelCase(prop)] = val;
                });
            },
            replace_outer: () => el.outerHTML = content,
            wrap: () => {
                const wrapper = doc.createElement('div');
                wrapper.innerHTML = content;
                const wrapperEl = wrapper.firstElementChild;
                if (wrapperEl) {
                    el.parentNode.insertBefore(wrapperEl, el);
                    wrapperEl.appendChild(el);
                }
            },
            unwrap: () => {
                const parent = el.parentNode;
                while (el.firstChild) parent.insertBefore(el.firstChild, el);
                el.remove();
            },
            clear: () => el.innerHTML = ''
        };

        if (!ops[operation]) return { success: false, error: `Unknown op` };
        
        try {
            ops[operation]();
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    // Get current artifact content (for get_artifact tool)
    getContent(selector = '', includeStyles = false) {
        const iframe = document.getElementById('artifact-iframe');
        const doc = iframe?.contentDocument;
        if (!doc) return { success: false, error: 'No artifact loaded' };

        try {
            if (selector) {
                const el = doc.querySelector(selector);
                if (!el) return { success: false, error: `Element not found: ${selector}` };
                return { 
                    success: true, 
                    selector,
                    outerHTML: el.outerHTML,
                    innerHTML: el.innerHTML,
                    tagName: el.tagName.toLowerCase(),
                    children: Array.from(el.children).map(c => ({
                        tag: c.tagName.toLowerCase(),
                        id: c.id || null,
                        classes: Array.from(c.classList)
                    }))
                };
            }

            // Full document
            let content = doc.documentElement.outerHTML;
            const structure = this._getDocumentStructure(doc);
            
            if (!includeStyles) {
                // Summarize styles instead of including full content
                const styles = doc.querySelectorAll('style');
                const styleInfo = Array.from(styles).map(s => ({
                    id: s.id || null,
                    rules: s.sheet?.cssRules?.length || 0
                }));
                return { success: true, structure, styles: styleInfo };
            }

            return { success: true, content, structure };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    // Get document structure for context
    _getDocumentStructure(doc) {
        const body = doc.body;
        if (!body) return [];

        const getStructure = (el, depth = 0) => {
            if (depth > 3) return null; // Limit depth
            const children = Array.from(el.children).slice(0, 10); // Limit children
            return {
                tag: el.tagName.toLowerCase(),
                id: el.id || undefined,
                classes: el.classList.length ? Array.from(el.classList).join(' ') : undefined,
                children: children.map(c => getStructure(c, depth + 1)).filter(Boolean)
            };
        };

        return getStructure(body);
    },

    _commitVersion(doc) {
        const html = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
        this.addVersion(html);
    },

    _injectStyle(doc, selector, css) {
        let style = doc.getElementById('dynamic-styles');
        if (!style) {
            style = doc.createElement('style');
            style.id = 'dynamic-styles';
            doc.head.appendChild(style);
        }
        style.textContent += `\n${selector} { ${css} }`;
    },

    _camelCase(str) {
        return str.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    },

    // ==================== UI RENDERING ====================

    render() {
        if (!this.els.panel) return;
        
        this.renderTabs();
        this.renderHeader();
        this.renderVersions();
        this.renderContent();
        
        this.els.panel.classList.toggle('open', this.isOpen && this.activeId);
    },

    renderTabs() {
        const ids = Object.keys(this.artifacts);
        if (ids.length <= 1) {
            this.els.tabs.innerHTML = '';
            this.els.tabs.style.display = 'none';
            return;
        }

        this.els.tabs.style.display = 'flex';
        this.els.tabs.innerHTML = ids.map(id => {
            const art = this.artifacts[id];
            const active = id === this.activeId ? 'active' : '';
            const shortTitle = art.title.slice(0, 20) + (art.title.length > 20 ? '…' : '');
            return `
                <div class="artifact-tab ${active}" onclick="ArtifactManager.select('${id}')">
                    <span>${this._escapeHtml(shortTitle)}</span>
                    <button class="tab-close" onclick="event.stopPropagation(); ArtifactManager.delete('${id}')">×</button>
                </div>
            `;
        }).join('');
    },

    renderHeader() {
        const art = this.artifacts[this.activeId];
        this.els.title.textContent = art?.title || 'Artifact';
    },

    renderVersions() {
        const art = this.artifacts[this.activeId];
        if (!art || art.versions.length <= 1) {
            this.els.versions.style.display = 'none';
            return;
        }

        this.els.versions.style.display = 'inline-block';
        this.els.versions.innerHTML = art.versions.map((_, i) => 
            `<option value="${i}" ${i === this.activeVersion ? 'selected' : ''}>V${i + 1}</option>`
        ).join('');
    },

    renderContent() {
        const art = this.artifacts[this.activeId];
        if (!art) {
            this.els.content.innerHTML = '<div class="artifact-empty">Aucun artifact</div>';
            return;
        }

        const version = art.versions[this.activeVersion];
        if (!version) return;

        this.els.content.className = 'artifact-content';
        
        if (this.view === 'code') {
            this.els.content.classList.add('code-mode');
            this.els.content.innerHTML = `<pre><code class="language-html">${this._escapeHtml(version.content)}</code></pre>`;
            if (window.hljs) hljs.highlightElement(this.els.content.querySelector('code'));
        } else {
            const iframe = document.createElement('iframe');
            iframe.id = 'artifact-iframe';
            iframe.sandbox = 'allow-scripts allow-same-origin';
            iframe.srcdoc = version.content;
            this.els.content.innerHTML = '';
            this.els.content.appendChild(iframe);
        }
    },

    // ==================== ACTIONS ====================

    toggleView() {
        this.view = this.view === 'preview' ? 'code' : 'preview';
        this.els.viewIcon.textContent = this.view === 'preview' ? '📝' : '👁️';
        this.renderContent();
    },

    copyCode() {
        const art = this.artifacts[this.activeId];
        const content = art?.versions[this.activeVersion]?.content || '';
        navigator.clipboard.writeText(content).then(() => {
            const btn = document.querySelector('.artifact-btn[onclick*="copyCode"]');
            if (btn) {
                const orig = btn.textContent;
                btn.textContent = '✓';
                setTimeout(() => btn.textContent = orig, 1500);
            }
        });
    },

    close() {
        this.isOpen = false;
        this.els.panel.classList.remove('open');
        this.save();
    },

    open() {
        if (this.activeId) {
            this.isOpen = true;
            this.els.panel.classList.add('open');
            this.save();
        }
    },

    clear() {
        this.artifacts = {};
        this.activeId = null;
        this.activeVersion = 0;
        this.isOpen = false;
        this.save();
        this.render();
    },

    // ==================== HELPERS ====================

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    getCurrentVersion() {
        return this.activeVersion + 1;
    },

    getVersionCount() {
        const art = this.artifacts[this.activeId];
        return art ? art.versions.length : 0;
    },

    generateId() {
        return 'art_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    }
};

// Global functions for HTML onclick
function closeArtifact() { ArtifactManager.close(); }
function selectArtifactVersion(sel) { ArtifactManager.selectVersion(parseInt(sel.value)); }
