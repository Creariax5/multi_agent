"""Client for Memory Service API"""
import logging
import httpx
from config import MEMORY_SERVICE_URL

logger = logging.getLogger(__name__)


async def save_message(telegram_chat_id: str, role: str, content: str, conversation_id: str = None) -> bool:
    """Save a message to memory service."""
    try:
        # Use telegram_chat_id as conversation_id if not provided
        conv_id = conversation_id or f"telegram_{telegram_chat_id}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/conversations/message",
                json={
                    "conversation_id": conv_id,
                    "role": role,
                    "content": content,
                    "telegram_chat_id": telegram_chat_id
                }
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to save message to memory: {e}")
        return False


async def get_recent_messages(telegram_chat_id: str, limit: int = 20) -> list:
    """Get recent messages for a user from memory service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{MEMORY_SERVICE_URL}/conversations/user/{telegram_chat_id}/recent-messages",
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json().get("messages", [])
    except Exception as e:
        logger.warning(f"Failed to get messages from memory: {e}")
    return []


async def link_account(telegram_chat_id: str, account_type: str, account_identifier: str) -> bool:
    """Link an external account to the user."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/accounts/link",
                json={
                    "telegram_chat_id": telegram_chat_id,
                    "account_type": account_type,
                    "account_identifier": account_identifier
                }
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to link account: {e}")
        return False


async def get_linked_accounts(telegram_chat_id: str) -> list:
    """Get all linked accounts for a user."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{MEMORY_SERVICE_URL}/accounts/{telegram_chat_id}"
            )
            if response.status_code == 200:
                return response.json().get("accounts", [])
    except Exception as e:
        logger.warning(f"Failed to get linked accounts: {e}")
    return []
