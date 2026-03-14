"""
Telegram Bot integration for IntelliKnow KMS
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.services.orchestrator_wrapper import get_orchestrator

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram Bot for IntelliKnow KMS"""

    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command
        """
        welcome_message = """🤖 Welcome to IntelliKnow KMS!

I'm your AI-powered knowledge management assistant.

Here's how I can help you:
• Ask questions about company policies and procedures
• Search our knowledge base for relevant information
• Get quick answers to common questions

Example questions:
• "What is the annual leave policy?"
• "How do I submit an expense report?"
• "What are the working hours?"

Use /help to see all available commands."""

        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /help command
        """
        help_message = """📚 IntelliKnow KMS Commands:

/start - Welcome message
/help - Show this help message
/stats - View system statistics

Just type your question to get started! I'll search our knowledge base and provide relevant answers.

Supported topics: HR, Legal, Finance, and more."""

        await update.message.reply_text(help_message)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /stats command
        """
        try:
            db = SessionLocal()
            try:
                from backend.models.database import Document, Query

                doc_count = db.query(Document).count()
                query_count = db.query(Query).count()

                stats_message = f"""📊 System Statistics:

📄 Documents: {doc_count}
❓ Total Queries: {query_count}

The knowledge base is growing!"""

                await update.message.reply_text(stats_message)

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            await update.message.reply_text("Sorry, I couldn't fetch the statistics at the moment.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle incoming text messages
        """
        try:
            user_message = update.message.text.strip()

            logger.info(f"Received message from Telegram: {user_message}")

            # Send typing indicator
            await update.message.chat.send_action("typing")

            # Process query
            orchestrator_instance = get_orchestrator()
            result = orchestrator_instance.process_query(
                user_message,
                "telegram",
                user_id=str(update.effective_user.id)
            )

            # Format response with platform-specific formatting and sources
            from backend.utils.response_formatter import ResponseFormatter
            response = ResponseFormatter.format_response("telegram", result, include_sources=True)

            # Send response
            await update.message.reply_text(response, parse_mode='Markdown')

            logger.info(f"Sent response to Telegram: {len(response)} chars")

        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")
            await update.message.reply_text(
                "I apologize, but I encountered an error. Please try again later."
            )

    def run(self):
        """
        Run the bot (blocking)
        """
        logger.info("Starting Telegram bot...")
        self.application.run_polling(drop_pending_updates=True)


def create_telegram_bot(token: str) -> TelegramBot:
    """Factory function to create Telegram bot"""
    return TelegramBot(token)


# If running directly
if __name__ == "__main__":
    import os
    from backend.config import settings

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        exit(1)

    bot = create_telegram_bot(settings.telegram_bot_token)
    bot.run()
