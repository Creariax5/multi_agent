"""Conversation storage per user"""

# In-memory storage: {user_id: {"messages": [...], "model": "...", "multi_msg": bool}}
_conversations = {}

MAX_HISTORY = 20  # Max messages to keep


def get_conversation(user_id: int) -> dict:
    """Get or create conversation for user"""
    if user_id not in _conversations:
        _conversations[user_id] = {"messages": [], "model": "gpt-4.1", "multi_msg": False}
    # Migration for existing conversations
    if "multi_msg" not in _conversations[user_id]:
        _conversations[user_id]["multi_msg"] = False
    return _conversations[user_id]


def add_message(user_id: int, role: str, content: str):
    """Add message to conversation"""
    conv = get_conversation(user_id)
    conv["messages"].append({"role": role, "content": content})
    
    # Trim old messages
    if len(conv["messages"]) > MAX_HISTORY:
        conv["messages"] = conv["messages"][-MAX_HISTORY:]


def get_messages(user_id: int) -> list:
    """Get conversation messages"""
    return get_conversation(user_id)["messages"]


def clear_conversation(user_id: int):
    """Clear conversation for user"""
    if user_id in _conversations:
        _conversations[user_id]["messages"] = []


def set_model(user_id: int, model: str):
    """Set model for user"""
    get_conversation(user_id)["model"] = model


def get_model(user_id: int) -> str:
    """Get model for user"""
    return get_conversation(user_id)["model"]


def set_multi_msg(user_id: int, enabled: bool):
    """Set multi-message mode for user"""
    get_conversation(user_id)["multi_msg"] = enabled


def get_multi_msg(user_id: int) -> bool:
    """Get multi-message mode for user"""
    return get_conversation(user_id)["multi_msg"]
