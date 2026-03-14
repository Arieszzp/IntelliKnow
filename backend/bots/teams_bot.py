"""
Microsoft Teams Bot integration for IntelliKnow KMS
"""
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
import logging
from sqlalchemy.orm import Session

from backend.services.orchestrator_wrapper import get_orchestrator

logger = logging.getLogger(__name__)


class TeamsBot(ActivityHandler):
    """Teams Bot for IntelliKnow KMS"""

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming messages from Teams
        """
        try:
            # Get user message
            user_message = turn_context.activity.text.strip()

            logger.info(f"Received message from Teams: {user_message}")

            # Process query
            orchestrator_instance = get_orchestrator()
            result = orchestrator_instance.process_query(
                user_message,
                "teams",
                user_id=turn_context.activity.from_property.id
            )

            # New orchestrator already returns formatted response
            response = result.get('response') or result.get('answer') or 'No response generated'

            # Send response
            await turn_context.send_activity(MessageFactory.text(response))

            logger.info(f"Sent response to Teams: {len(response)} chars")

        except Exception as e:
            logger.error(f"Error processing Teams message: {e}")
            await turn_context.send_activity(
                MessageFactory.text("I apologize, but I encountered an error. Please try again later.")
            )

    async def on_members_added_activity(
        self,
        members_added: list[ChannelAccount],
        turn_context: TurnContext
    ):
        """
        Send welcome message when bot is added to a conversation
        """
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = """Welcome to IntelliKnow KMS! 🤖

I'm your AI-powered knowledge management assistant. Here's how you can interact with me:

• Ask questions about company policies, procedures, and information
• I'll search our knowledge base to find relevant answers
• I can help with HR, Legal, Finance, and other topics

Example questions:
- "What is the annual leave policy?"
- "How do I submit an expense report?"
- "What are the working hours?"

Just type your question, and I'll do my best to help! 📚"""
                await turn_context.send_activity(MessageFactory.text(welcome_message))


def create_teams_bot():
    """Factory function to create the bot"""
    return TeamsBot()


# If running directly (for testing)
if __name__ == "__main__":
    from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings

    # This would be called from a web server
    # See main.py for the full setup
    pass
