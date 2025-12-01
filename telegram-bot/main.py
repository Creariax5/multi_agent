"""Telegram Bot - Entry point"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TELEGRAM_BOT_TOKEN
from handlers import start, help_command, new_conversation, select_model, model_callback, handle_message, toggle_mode

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot"""
    logger.info("🤖 Starting Telegram Bot...")
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_conversation))
    app.add_handler(CommandHandler("model", select_model))
    app.add_handler(CommandHandler("mode", toggle_mode))
    app.add_handler(CallbackQueryHandler(model_callback, pattern="^model:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot ready! Polling...")
    
    # Run
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
