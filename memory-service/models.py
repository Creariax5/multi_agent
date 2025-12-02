"""
Database models for memory service.
Uses SQLite with aiosqlite for async operations.
"""
import aiosqlite
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path("/app/data/memory.db")


async def init_db():
    """Initialize the database with all required tables."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table - core user identity
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_chat_id TEXT UNIQUE,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Linked accounts - email, slack, etc. linked to a user
        await db.execute("""
            CREATE TABLE IF NOT EXISTS linked_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                account_identifier TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(account_type, account_identifier)
            )
        """)
        
        # Trigger configs - per-user trigger settings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trigger_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, source_type)
            )
        """)
        
        # Memories - for RAG/context persistence
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT DEFAULT 'general',
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Conversations - full conversation history
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        await db.commit()
        print("✅ Database initialized")


async def get_db():
    """Get a database connection."""
    return await aiosqlite.connect(DATABASE_PATH)


# ==================== User Operations ====================

async def get_or_create_user(telegram_chat_id: str, username: str = None) -> dict:
    """Get user by telegram chat ID, or create if doesn't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_chat_id = ?",
            (telegram_chat_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return dict(row)
        
        # Create new user
        cursor = await db.execute(
            "INSERT INTO users (telegram_chat_id, username) VALUES (?, ?)",
            (telegram_chat_id, username)
        )
        await db.commit()
        
        return {
            "id": cursor.lastrowid,
            "telegram_chat_id": telegram_chat_id,
            "username": username
        }


async def get_user_by_linked_account(account_type: str, account_identifier: str) -> dict | None:
    """Find user by a linked account (e.g., email)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT u.* FROM users u
            JOIN linked_accounts la ON u.id = la.user_id
            WHERE la.account_type = ? AND la.account_identifier = ?
        """, (account_type, account_identifier))
        
        row = await cursor.fetchone()
        return dict(row) if row else None


# ==================== Linked Account Operations ====================

async def link_account(user_id: int, account_type: str, account_identifier: str) -> dict:
    """Link an external account (email, slack, etc.) to a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO linked_accounts (user_id, account_type, account_identifier) VALUES (?, ?, ?)",
                (user_id, account_type, account_identifier)
            )
            await db.commit()
            return {"success": True, "id": cursor.lastrowid}
        except aiosqlite.IntegrityError:
            return {"success": False, "error": "Account already linked"}


async def get_linked_accounts(user_id: int) -> list:
    """Get all accounts linked to a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT * FROM linked_accounts WHERE user_id = ?",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def unlink_account(user_id: int, account_type: str, account_identifier: str) -> bool:
    """Remove a linked account."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM linked_accounts WHERE user_id = ? AND account_type = ? AND account_identifier = ?",
            (user_id, account_type, account_identifier)
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== Trigger Config Operations ====================

async def get_trigger_config(user_id: int, source_type: str) -> dict | None:
    """Get trigger config for a specific source."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT * FROM trigger_configs WHERE user_id = ? AND source_type = ?",
            (user_id, source_type)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_trigger_config(user_id: int, source_type: str, enabled: bool = True, instructions: str = None) -> dict:
    """Set or update trigger config for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO trigger_configs (user_id, source_type, enabled, instructions)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, source_type) DO UPDATE SET
                enabled = excluded.enabled,
                instructions = excluded.instructions,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, source_type, int(enabled), instructions))
        await db.commit()
        return {"success": True}


async def get_all_trigger_configs(user_id: int) -> list:
    """Get all trigger configs for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT * FROM trigger_configs WHERE user_id = ?",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ==================== Memory Operations (RAG) ====================

async def add_memory(content: str, user_id: int = None, category: str = "general", metadata: str = None) -> dict:
    """Add a memory for RAG retrieval."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO memories (user_id, category, content, metadata) VALUES (?, ?, ?, ?)",
            (user_id, category, content, metadata)
        )
        await db.commit()
        return {"success": True, "id": cursor.lastrowid}


async def search_memories(query: str, user_id: int = None, category: str = None, limit: int = 10) -> list:
    """Search memories (simple LIKE search - can be enhanced with vector search later)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        sql = "SELECT * FROM memories WHERE content LIKE ?"
        params = [f"%{query}%"]
        
        if user_id is not None:
            sql += " AND (user_id = ? OR user_id IS NULL)"
            params.append(user_id)
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_recent_memories(user_id: int = None, limit: int = 20) -> list:
    """Get recent memories."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if user_id:
            cursor = await db.execute(
                "SELECT * FROM memories WHERE user_id = ? OR user_id IS NULL ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ==================== Conversation Operations ====================

async def save_conversation_message(conversation_id: str, role: str, content: str, user_id: int = None) -> dict:
    """Save a conversation message."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (user_id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (user_id, conversation_id, role, content)
        )
        await db.commit()
        return {"success": True, "id": cursor.lastrowid}


async def get_conversation(conversation_id: str) -> list:
    """Get all messages in a conversation."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_conversations(user_id: int, limit: int = 50) -> list:
    """Get recent conversations for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT DISTINCT conversation_id, MIN(created_at) as started_at
            FROM conversations
            WHERE user_id = ?
            GROUP BY conversation_id
            ORDER BY started_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
