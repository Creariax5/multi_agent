"""
API routes for memory service.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import models

router = APIRouter()


# ==================== Pydantic Models ====================

class UserCreate(BaseModel):
    telegram_chat_id: str
    username: Optional[str] = None


class LinkAccountRequest(BaseModel):
    telegram_chat_id: str
    account_type: str  # "email", "slack", etc.
    account_identifier: str  # email address, slack user id, etc.


class UnlinkAccountRequest(BaseModel):
    telegram_chat_id: str
    account_type: str
    account_identifier: str


class TriggerConfigRequest(BaseModel):
    telegram_chat_id: str
    source_type: str  # "email", "stripe", "calendar", etc.
    enabled: bool = True
    instructions: Optional[str] = None


class MemoryRequest(BaseModel):
    content: str
    telegram_chat_id: Optional[str] = None
    category: str = "general"
    metadata: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str
    telegram_chat_id: Optional[str] = None
    category: Optional[str] = None
    limit: int = 10


class ConversationMessageRequest(BaseModel):
    conversation_id: str
    role: str
    content: str
    telegram_chat_id: Optional[str] = None


class LookupByAccountRequest(BaseModel):
    account_type: str
    account_identifier: str


# ==================== User Routes ====================

@router.post("/users")
async def create_or_get_user(request: UserCreate):
    """Create a new user or get existing one by telegram chat ID."""
    user = await models.get_or_create_user(request.telegram_chat_id, request.username)
    return user


@router.get("/users/{telegram_chat_id}")
async def get_user(telegram_chat_id: str):
    """Get user by telegram chat ID."""
    user = await models.get_or_create_user(telegram_chat_id)
    return user


@router.post("/users/lookup-by-account")
async def lookup_user_by_account(request: LookupByAccountRequest):
    """Find user by a linked account (e.g., find user by email)."""
    user = await models.get_user_by_linked_account(request.account_type, request.account_identifier)
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this linked account")
    return user


# ==================== Linked Account Routes ====================

@router.post("/accounts/link")
async def link_account(request: LinkAccountRequest):
    """Link an external account to a user."""
    user = await models.get_or_create_user(request.telegram_chat_id)
    result = await models.link_account(user["id"], request.account_type, request.account_identifier)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": f"Successfully linked {request.account_type}: {request.account_identifier}"}


@router.post("/accounts/unlink")
async def unlink_account(request: UnlinkAccountRequest):
    """Remove a linked account."""
    user = await models.get_or_create_user(request.telegram_chat_id)
    success = await models.unlink_account(user["id"], request.account_type, request.account_identifier)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": f"Successfully unlinked {request.account_type}: {request.account_identifier}"}


@router.get("/accounts/{telegram_chat_id}")
async def get_linked_accounts(telegram_chat_id: str):
    """Get all accounts linked to a user."""
    user = await models.get_or_create_user(telegram_chat_id)
    accounts = await models.get_linked_accounts(user["id"])
    return {"accounts": accounts}


# ==================== Trigger Config Routes ====================

@router.post("/triggers/config")
async def set_trigger_config(request: TriggerConfigRequest):
    """Set or update trigger configuration for a user."""
    user = await models.get_or_create_user(request.telegram_chat_id)
    await models.set_trigger_config(user["id"], request.source_type, request.enabled, request.instructions)
    return {"message": f"Trigger config for {request.source_type} updated"}


@router.get("/triggers/{telegram_chat_id}")
async def get_trigger_configs(telegram_chat_id: str):
    """Get all trigger configs for a user."""
    user = await models.get_or_create_user(telegram_chat_id)
    configs = await models.get_all_trigger_configs(user["id"])
    return {"configs": configs}


@router.get("/triggers/{telegram_chat_id}/{source_type}")
async def get_trigger_config(telegram_chat_id: str, source_type: str):
    """Get specific trigger config for a user."""
    user = await models.get_or_create_user(telegram_chat_id)
    config = await models.get_trigger_config(user["id"], source_type)
    return {"config": config}


# ==================== Memory Routes (RAG) ====================

@router.post("/memories")
async def add_memory(request: MemoryRequest):
    """Add a memory for RAG retrieval."""
    user_id = None
    if request.telegram_chat_id:
        user = await models.get_or_create_user(request.telegram_chat_id)
        user_id = user["id"]
    
    result = await models.add_memory(request.content, user_id, request.category, request.metadata)
    return result


@router.post("/memories/search")
async def search_memories(request: MemorySearchRequest):
    """Search memories."""
    user_id = None
    if request.telegram_chat_id:
        user = await models.get_or_create_user(request.telegram_chat_id)
        user_id = user["id"]
    
    memories = await models.search_memories(request.query, user_id, request.category, request.limit)
    return {"memories": memories}


@router.get("/memories/recent")
async def get_recent_memories(telegram_chat_id: str = None, limit: int = 20):
    """Get recent memories."""
    user_id = None
    if telegram_chat_id:
        user = await models.get_or_create_user(telegram_chat_id)
        user_id = user["id"]
    
    memories = await models.get_recent_memories(user_id, limit)
    return {"memories": memories}


# ==================== Conversation Routes ====================

@router.post("/conversations/message")
async def save_message(request: ConversationMessageRequest):
    """Save a conversation message."""
    user_id = None
    if request.telegram_chat_id:
        user = await models.get_or_create_user(request.telegram_chat_id)
        user_id = user["id"]
    
    result = await models.save_conversation_message(
        request.conversation_id, request.role, request.content, user_id
    )
    return result


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get all messages in a conversation."""
    messages = await models.get_conversation(conversation_id)
    return {"messages": messages}


@router.get("/conversations/user/{telegram_chat_id}")
async def get_user_conversations(telegram_chat_id: str, limit: int = 50):
    """Get recent conversations for a user."""
    user = await models.get_or_create_user(telegram_chat_id)
    conversations = await models.get_user_conversations(user["id"], limit)
    return {"conversations": conversations}
