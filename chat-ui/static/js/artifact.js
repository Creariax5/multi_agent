/**
 * Artifact Manager - Handle artifact display and editing in side panel
 */
const ArtifactManager = {
    store: {},
    panel: null,
    content: null,
    titleEl: null,
    currentArtifactId: null,

    init() {
        this.panel = document.getElementById('artifact-panel');
        this.content = document.getElementById('artifact-content');
        this.titleEl = document.getElementById('artifact-title');
    },

    render(title, content, type) {
        if (!this.panel) this.init();
        
        this.titleEl.textContent = title;
        this.content.innerHTML = '';
        this.content.className = 'artifact-content';

        if (type === 'html') {
            const iframe = document.createElement('iframe');
            iframe.id = 'artifact-iframe';
            iframe.sandbox = 'allow-scripts allow-same-origin';
            iframe.srcdoc = content;
            this.content.appendChild(iframe);
        } else {
            this.content.classList.add('code-mode');
            const pre = document.createElement('pre');
            const code = document.createElement('code');
            code.textContent = content;
            pre.appendChild(code);
            this.content.appendChild(pre);
            if (window.hljs) hljs.highlightElement(code);
        }

        this.panel.classList.add('open');
    },

    /**
     * Apply an edit operation to the current artifact
     */
    applyEdit(selector, operation, content, attribute) {
        const iframe = document.getElementById('artifact-iframe');
        if (!iframe) {
            console.warn('No artifact iframe found for edit');
            return false;
        }

        // Wait for iframe to be ready
        const doc = iframe.contentDocument || iframe.contentWindow?.document;
        if (!doc) {
            console.warn('Iframe document not accessible');
            return false;
        }

        // Skip pseudo-class selectors (can't be queried)
        if (selector.includes(':hover') || selector.includes(':focus') || 
            selector.includes(':active') || selector.includes('::')) {
            console.log('Skipping pseudo-selector:', selector);
            // For pseudo-classes, inject a <style> tag instead
            if (operation === 'set_style') {
                this.injectStyle(doc, selector, content);
                return true;
            }
            return false;
        }

        let element;
        try {
            element = doc.querySelector(selector);
        } catch (e) {
            console.warn('Invalid selector:', selector, e.message);
            return false;
        }
        
        if (!element) {
            // For append/prepend on body, try body directly
            if ((operation === 'append' || operation === 'prepend') && selector === 'body') {
                element = doc.body;
            }
            if (!element) {
                console.warn('Element not found:', selector);
                return false;
            }
        }

        try {
            switch (operation) {
                case 'replace':
                    element.innerHTML = content;
                    break;
                    
                case 'insert_after':
                    element.insertAdjacentHTML('afterend', content);
                    break;
                    
                case 'insert_before':
                    element.insertAdjacentHTML('beforebegin', content);
                    break;
                    
                case 'delete':
                    element.remove();
                    break;
                    
                case 'set_style':
                    // Content is CSS like "background: red; color: blue"
                    content.split(';').forEach(rule => {
                        const colonIdx = rule.indexOf(':');
                        if (colonIdx > 0) {
                            const prop = rule.slice(0, colonIdx).trim();
                            const val = rule.slice(colonIdx + 1).trim();
                            if (prop && val) {
                                element.style[this.camelCase(prop)] = val;
                            }
                        }
                    });
                    break;
                    
                case 'set_attribute':
                    element.setAttribute(attribute, content);
                    break;
                    
                case 'append':
                    element.insertAdjacentHTML('beforeend', content);
                    break;
                    
                case 'prepend':
                    element.insertAdjacentHTML('afterbegin', content);
                    break;
                    
                default:
                    console.warn('Unknown operation:', operation);
                    return false;
            }

            // Update stored content
            if (this.currentArtifactId && this.store[this.currentArtifactId]) {
                this.store[this.currentArtifactId].content = '<!DOCTYPE html>' + doc.documentElement.outerHTML;
            }

            return true;
        } catch (e) {
            console.warn('Edit failed:', e.message);
            return false;
        }
    },

    /**
     * Inject a <style> tag for pseudo-selectors
     */
    injectStyle(doc, selector, cssProperties) {
        let styleEl = doc.getElementById('artifact-dynamic-styles');
        if (!styleEl) {
            styleEl = doc.createElement('style');
            styleEl.id = 'artifact-dynamic-styles';
            doc.head.appendChild(styleEl);
        }
        styleEl.textContent += `\n${selector} { ${cssProperties} }`;
    },

    camelCase(str) {
        return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    },

    close() {
        if (this.panel) {
            this.panel.classList.remove('open');
        }
    },

    save(id, artifact) {
        this.store[id] = artifact;
        this.currentArtifactId = id;
    },

    get(id) {
        return this.store[id];
    },

    generateId() {
        return 'artifact_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
};

// Global close function for HTML onclick
function closeArtifact() {
    ArtifactManager.close();
}
