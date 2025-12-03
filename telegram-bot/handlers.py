"""Telegram bot handlers"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

import copilot_client
import conversations
import memory_client

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Salut! Je suis un assistant IA propulsé par GitHub Copilot.\n\n"
        "Commandes:\n"
        "/new - Nouvelle conversation\n"
        "/model - Changer de modèle\n"
        "/mode - Basculer mode multi-message\n"
        "/help - Aide\n\n"
        "Envoie-moi un message pour commencer!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id
    multi = "✅ activé" if conversations.get_multi_msg(user_id) else "❌ désactivé"
    
    await update.message.reply_text(
        "🤖 **Assistant IA**\n\n"
        "Je peux t'aider avec:\n"
        "• Répondre à des questions\n"
        "• Écrire du code\n"
        "• Créer des pages HTML\n"
        "• Et plus encore!\n\n"
        "**Commandes:**\n"
        "/new - Efface l'historique\n"
        "/model - Change le modèle IA\n"
        f"/mode - Mode multi-message ({multi})\n",
        parse_mode=ParseMode.MARKDOWN
    )


async def toggle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mode command - toggle multi-message mode"""
    user_id = update.effective_user.id
    current = conversations.get_multi_msg(user_id)
    new_mode = not current
    conversations.set_multi_msg(user_id, new_mode)
    
    if new_mode:
        await update.message.reply_text(
            "📨 **Mode multi-message activé**\n\n"
            "Tu recevras un message séparé pour:\n"
            "• 💭 Chaque réflexion (think)\n"
            "• 🔧 Chaque outil utilisé\n"
            "• 💬 Chaque réponse\n"
            "• 📄 Chaque artifact",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "📝 **Mode message simple activé**\n\n"
            "Tu recevras une seule réponse finale consolidée.",
            parse_mode=ParseMode.MARKDOWN
        )


async def new_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command"""
    user_id = update.effective_user.id
    conversations.clear_conversation(user_id)
    await update.message.reply_text("🔄 Nouvelle conversation! L'historique a été effacé.")


async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /model command"""
    models = await copilot_client.get_models()
    
    if not models:
        await update.message.reply_text("❌ Impossible de récupérer les modèles.")
        return
    
    # Create inline keyboard
    keyboard = []
    for m in models:
        model_id = m["id"]
        cost = m.get("cost", "?")
        keyboard.append([InlineKeyboardButton(f"{model_id} ({cost})", callback_data=f"model:{model_id}")])
    
    user_id = update.effective_user.id
    current = conversations.get_model(user_id)
    
    await update.message.reply_text(
        f"🤖 Modèle actuel: **{current}**\n\nChoisis un modèle:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle model selection callback"""
    query = update.callback_query
    await query.answer()
    
    model = query.data.replace("model:", "")
    user_id = update.effective_user.id
    conversations.set_model(user_id, model)
    
    await query.edit_message_text(f"✅ Modèle changé: **{model}**", parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    # Get local conversation history BEFORE adding new message
    local_messages = conversations.get_messages(user_id)
    
    # If local history is empty, load from memory-service (includes event-trigger messages)
    if len(local_messages) == 0:
        logger.info(f"Loading history from memory-service for chat {chat_id}")
        history = await memory_client.get_recent_messages(str(chat_id), limit=20)
        if history:
            logger.info(f"Loaded {len(history)} messages from memory-service")
            for msg in history:
                conversations.add_message(user_id, msg["role"], msg["content"])
    
    # Now add user message to local history
    conversations.add_message(user_id, "user", user_message)
    
    # Save to memory service (persistent)
    await memory_client.save_message(str(chat_id), "user", user_message)
    
    # Get updated messages
    messages = conversations.get_messages(user_id)
    model = conversations.get_model(user_id)
    multi_msg = conversations.get_multi_msg(user_id)
    
    logger.info(f"User {user_id}: {user_message[:50]}... (model: {model}, multi: {multi_msg}, history: {len(messages)})")
    
    try:
        if multi_msg:
            await _handle_multi_message(update, context, messages, model)
        else:
            await _handle_single_message(update, context, messages, model)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Erreur: {str(e)}")


async def _handle_multi_message(update: Update, context: ContextTypes.DEFAULT_TYPE, messages: list, model: str):
    """Handle message in multi-message mode - send each event as separate message"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    final_message = ""
    
    # Pass telegram context for tools that need it
    user_context = {"telegram_chat_id": str(chat_id), "telegram_user_id": str(user_id)}
    
    async for event in copilot_client.chat_stream(messages, model, user_context):
        t = event.get("type")
        
        # Keep typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        if t == "thinking":
            content = event["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            await _send_safe_message(context.bot, chat_id, f"💭 {content}")
        
        elif t == "tool_call":
            tc = event.get("tool_call", {})
            name = tc.get("name", "?")
            await _send_safe_message(context.bot, chat_id, f"🔧 Outil: {name}")
        
        elif t == "message":
            final_message = event["content"]
            await _send_long_message(context.bot, chat_id, f"💬 {final_message}")
        
        elif t == "artifact":
            title = event.get("title", "Artifact")
            content = event.get("content", "")
            art_type = event.get("artifact_type", "")
            
            if "html" in art_type.lower():
                await _send_safe_message(context.bot, chat_id, f"📄 {title} (HTML créé)")
            else:
                snippet = content[:300] + "..." if len(content) > 300 else content
                await _send_safe_message(context.bot, chat_id, f"📄 {title}\n{snippet}")
        
        elif t == "error":
            await _send_safe_message(context.bot, chat_id, f"❌ {event['content']}")
    
    # Add final message to history (local + persistent)
    if final_message:
        conversations.add_message(user_id, "assistant", final_message)
        await memory_client.save_message(str(chat_id), "assistant", final_message)


async def _handle_single_message(update: Update, context: ContextTypes.DEFAULT_TYPE, messages: list, model: str):
    """Handle message in single-message mode - collect and send one response"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Pass telegram context for tools that need it
    user_context = {"telegram_chat_id": str(chat_id), "telegram_user_id": str(user_id)}
    
    result = await copilot_client.chat(messages, model, user_context)
    
    # Build response
    response_parts = []
    
    # Thinking (collapsed)
    if result["thinking"]:
        thinking = "\n".join(result["thinking"])
        if len(thinking) > 200:
            thinking = thinking[:200] + "..."
        response_parts.append(f"💭 _{thinking}_\n")
    
    # Messages
    if result["messages"]:
        response_parts.append("\n".join(result["messages"]))
    
    # Artifacts
    for artifact in result["artifacts"]:
        title = artifact.get("title", "Artifact")
        content = artifact.get("content", "")
        art_type = artifact.get("artifact_type", "")
        
        if "html" in art_type.lower():
            response_parts.append(f"\n📄 **{title}** (HTML créé)")
        else:
            if len(content) > 500:
                content = content[:500] + "\n..."
            response_parts.append(f"\n📄 **{title}**\n```\n{content}\n```")
    
    response = "\n".join(response_parts) or "🤔 Pas de réponse."
    
    # Add assistant message to history (local + persistent)
    if result["messages"]:
        final_msg = "\n".join(result["messages"])
        conversations.add_message(user_id, "assistant", final_msg)
        await memory_client.save_message(str(chat_id), "assistant", final_msg)
    
    await _send_long_message(context.bot, update.effective_chat.id, response, parse_mode=ParseMode.MARKDOWN)


async def _send_safe_message(bot, chat_id: int, text: str):
    """Send a message without markdown to avoid parse errors"""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")


async def _send_long_message(bot, chat_id: int, text: str, parse_mode=None):
    """Send message, splitting if too long. Falls back to plain text if markdown fails."""
    try:
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                try:
                    await bot.send_message(chat_id=chat_id, text=text[i:i+4000], parse_mode=parse_mode)
                except Exception:
                    # Fallback to plain text if markdown fails
                    await bot.send_message(chat_id=chat_id, text=text[i:i+4000])
        else:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        # Fallback to plain text if markdown fails
        logger.warning(f"Markdown parse error, falling back to plain text: {e}")
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e2:
            logger.error(f"Failed to send message: {e2}")
