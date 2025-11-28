/**
 * SSE Parser - Parse Server-Sent Events from a stream
 */
class SSEParser {
    constructor(onEvent, onError) {
        this.onEvent = onEvent;
        this.onError = onError || console.error;
        this.buffer = '';
    }

    async processStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            this.buffer += decoder.decode(value, { stream: true });
            this.parseBuffer();
        }
    }

    parseBuffer() {
        // SSE messages end with double newline
        let idx;
        while ((idx = this.buffer.indexOf('\n\n')) !== -1) {
            const message = this.buffer.slice(0, idx);
            this.buffer = this.buffer.slice(idx + 2);
            this.parseMessage(message);
        }
    }

    parseMessage(message) {
        // Collect all data lines
        let data = '';
        for (const line of message.split('\n')) {
            if (line.startsWith('data: ')) {
                data += line.slice(6);
            } else if (line.startsWith('data:')) {
                data += line.slice(5);
            }
        }

        if (!data || data === '[DONE]') return;

        try {
            const parsed = JSON.parse(data);
            console.log('SSE EVENT:', parsed.type || 'chunk', parsed);
            this.onEvent(parsed);
        } catch (e) {
            console.error('SSE Parse Error:', e.message);
            console.error('Raw data (first 500 chars):', data.substring(0, 500));
            // Don't call onError for parse errors, just log them
        }
    }
}
