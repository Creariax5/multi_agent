# 🔄 Flux de Données - Diagrammes Séquence

## 1️⃣ Chat Flow (Browser → AI → Response)

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant UI as 📺 Chat-UI
    participant CP as 🧠 Copilot-Proxy
    participant GH as 🤖 GitHub Copilot
    participant MCP as 🔧 MCP-Server
    participant ZB as 🔗 Zapier-Bridge
    participant MS as 💾 Memory-Service
    participant TG as 📱 Telegram

    rect rgb(230, 245, 255)
        Note over U,UI: Chat Flow
        U->>UI: Send message
        UI->>CP: POST /v1/chat/completions
        CP->>GH: Get Token
        GH-->>CP: Bearer Token
        CP->>MCP: GET /tools
        MCP->>ZB: GET /tools (Zapier)
        ZB-->>MCP: Zapier tools
        MCP-->>CP: All tools (23 local + Zapier)
    end

    rect rgb(255, 243, 224)
        Note over CP,GH: Agentic Loop (max 15 iterations)
        loop Until task_complete() or max iterations
            CP->>GH: Stream completion with tools
            GH-->>CP: Tool calls (think, send_message, etc.)
            CP->>MCP: POST /execute_batch
            alt Tool is think/send_message
                MCP-->>CP: Result
                CP-->>UI: SSE: thinking_delta / message_delta
            else Tool is create_artifact
                MCP-->>CP: Result
                CP-->>UI: SSE: artifact event
            else Tool is send_telegram
                MCP->>TG: sendMessage API
                TG-->>MCP: OK
                MCP-->>CP: Result
            else Tool is remember/recall
                MCP->>MS: POST /memories
                MS-->>MCP: OK
                MCP-->>CP: Result
            else Tool is task_complete
                MCP-->>CP: Terminal signal
                Note over CP: Exit loop
            end
            CP->>CP: Add tool results to messages
        end
    end

    CP-->>UI: SSE: [DONE]
    UI-->>U: Render response + artifacts
```

---

## 2️⃣ Event Trigger Flow (Webhooks → AI → Notification)

```mermaid
sequenceDiagram
    autonumber
    participant EXT as 📨 External Service<br/>(Gmail/Stripe/Slack)
    participant N8N as 🔌 N8N
    participant ET as 🎯 Event-Trigger
    participant MS as 💾 Memory-Service
    participant CP as 🧠 Copilot-Proxy
    participant MCP as 🔧 MCP-Server
    participant TG as 📱 Telegram

    rect rgb(255, 235, 238)
        Note over EXT,ET: Webhook Reception
        EXT->>N8N: Event (email received)
        N8N->>ET: POST /webhook/email
        ET->>ET: registry.get_source("email")
        ET->>ET: format_event(data)
    end

    rect rgb(232, 245, 233)
        Note over ET,MS: User Lookup
        ET->>MS: POST /users/lookup-by-account<br/>{type: "email", identifier: "user@example.com"}
        MS-->>ET: {telegram_chat_id: "123456"}
        ET->>MS: GET /conversations/user/123456/recent-messages
        MS-->>ET: [previous messages for context]
    end

    rect rgb(255, 243, 224)
        Note over ET,TG: AI Processing
        ET->>CP: POST /v1/chat/completions<br/>{messages, context}
        CP->>CP: Agentic Loop
        CP->>MCP: Execute send_telegram
        MCP->>TG: sendMessage({chat_id: "123456", text: "📧 New email from..."})
        TG-->>MCP: OK
        MCP-->>CP: Success
        CP-->>ET: Response
    end

    ET->>MS: POST /conversations/message<br/>(save for history)
```

---

## 3️⃣ Telegram Bot Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 User (Telegram)
    participant TG as 📱 Telegram API
    participant TB as 🤖 Telegram-Bot
    participant MS as 💾 Memory-Service
    participant CP as 🧠 Copilot-Proxy

    rect rgb(227, 242, 253)
        Note over U,TB: Message Reception
        U->>TG: Send message
        TG->>TB: getUpdates (polling)
        TB->>TB: handlers.handle_message()
    end

    rect rgb(232, 245, 233)
        Note over TB,MS: Context Loading
        TB->>MS: GET /conversations/user/{chat_id}/recent-messages
        MS-->>TB: [previous messages]
        TB->>MS: POST /conversations/message (save user msg)
    end

    rect rgb(255, 243, 224)
        Note over TB,CP: AI Processing
        TB->>CP: POST /v1/chat/completions<br/>{messages, user_context: {telegram_chat_id}}
        
        alt Multi-message mode
            loop Each event
                CP-->>TB: SSE event (thinking/tool/message)
                TB->>TG: sendMessage (for each event)
                TG-->>U: Display message
            end
        else Single-message mode
            CP-->>TB: Collected response
            TB->>TG: sendMessage (final)
            TG-->>U: Display message
        end
    end

    TB->>MS: POST /conversations/message (save assistant msg)
```

---

## 4️⃣ Agentic Loop Detail

```mermaid
flowchart TD
    Start([Start]) --> PrepareMessages[Prepare messages<br/>+ system prompt]
    PrepareMessages --> StreamCopilot[Stream to GitHub Copilot API]
    StreamCopilot --> CollectToolCalls{Tool calls<br/>received?}
    
    CollectToolCalls -->|No| Done([Done])
    CollectToolCalls -->|Yes| ExecuteTools[Execute tools via MCP]
    
    ExecuteTools --> ProcessResults[Process results]
    ProcessResults --> CheckTerminal{Terminal tool<br/>called?}
    
    CheckTerminal -->|Yes - task_complete| Done
    CheckTerminal -->|No| EmitEvents[Emit UI events<br/>thinking, message, artifact]
    
    EmitEvents --> AddToMessages[Add tool results<br/>to messages]
    AddToMessages --> CheckIterations{Max iterations<br/>reached?}
    
    CheckIterations -->|Yes - 15 max| Done
    CheckIterations -->|No| StreamCopilot
    
    style Start fill:#e8f5e9
    style Done fill:#ffebee
    style CheckTerminal fill:#fff3e0
    style CheckIterations fill:#fff3e0
```

---

## 5️⃣ Memory & RAG Flow

```mermaid
flowchart LR
    subgraph Input["Input Sources"]
        Chat[💬 Chat Messages]
        Events[📨 Event Triggers]
        Tools[🔧 Tool Calls]
    end

    subgraph MemoryService["💾 Memory Service"]
        API[REST API]
        subgraph Storage["SQLite Storage"]
            Users[(users)]
            Accounts[(linked_accounts)]
            Configs[(trigger_configs)]
            Memories[(memories)]
            Convs[(conversations)]
        end
    end

    subgraph Output["Output Uses"]
        Context[📝 Context Injection]
        UserLookup[👤 User Lookup]
        History[📜 History Loading]
    end

    Chat -->|save_message| API
    Events -->|lookup_by_account| API
    Tools -->|remember/recall| API

    API --> Storage

    Storage --> Context
    Storage --> UserLookup
    Storage --> History

    Context --> CopilotProxy[🧠 Copilot-Proxy]
    UserLookup --> EventTrigger[🎯 Event-Trigger]
    History --> TelegramBot[📱 Telegram-Bot]
```
