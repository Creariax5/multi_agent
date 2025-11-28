/**
 * Conversation Manager - Handle conversations and storage
 */
const ConversationManager = {
    conversations: [],
    current: null,
    messages: [],

    init() {
        this.load();
    },

    load() {
        const saved = localStorage.getItem('conversations');
        if (saved) {
            try {
                this.conversations = JSON.parse(saved);
            } catch (e) {
                console.error('Error loading conversations:', e);
                this.conversations = [];
            }
        }
    },

    save() {
        localStorage.setItem('conversations', JSON.stringify(this.conversations));
    },

    create(title, model) {
        this.current = {
            id: Date.now(),
            title,
            messages: [...this.messages],
            model,
            createdAt: new Date().toISOString()
        };
        this.conversations.unshift(this.current);
        this.save();
        return this.current;
    },

    update() {
        if (this.current) {
            this.current.messages = [...this.messages];
            this.current.updatedAt = new Date().toISOString();
            this.save();
        }
    },

    delete(id) {
        this.conversations = this.conversations.filter(c => c.id !== id);
        this.save();
        if (this.current?.id === id) {
            this.current = null;
            this.messages = [];
        }
    },

    get(id) {
        return this.conversations.find(c => c.id === id);
    },

    setCurrent(id) {
        const conv = this.get(id);
        if (conv) {
            this.current = conv;
            this.messages = [...conv.messages];
        }
        return conv;
    },

    clear() {
        this.messages = [];
        this.current = null;
    },

    addMessage(message) {
        this.messages.push(message);
        if (this.current) {
            this.update();
        } else if (this.messages.length > 0) {
            const title = this.messages[0].content.substring(0, 30) + 
                         (this.messages[0].content.length > 30 ? '...' : '');
            this.create(title, localStorage.getItem('selectedModel') || 'gpt-4.1');
        }
    }
};
