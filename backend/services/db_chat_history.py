"""
Database-backed ChatMessageHistory for LangChain
"""
from typing import List, Dict
from langchain.schema import BaseChatMessageHistory
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain ChatMessageHistory backed by database

    This class integrates LangChain's memory system with our database
    """

    def __init__(self, conversation_id: int, db: Session):
        """
        Initialize database chat history

        Args:
            conversation_id: Database conversation ID
            db: SQLAlchemy database session
        """
        self.conversation_id = conversation_id
        self.db = db
        self._cache: List[BaseMessage] = []
        self._loaded = False

        logger.debug(f"DatabaseChatMessageHistory initialized for conversation {conversation_id}")

    @property
    def messages(self) -> List[BaseMessage]:
        """
        Load messages from database

        Returns:
            List of LangChain messages
        """
        if not self._loaded:
            self._load_messages()
        return self._cache

    def add_message(self, message: BaseMessage) -> None:
        """
        Add a message to history and save to database

        Args:
            message: LangChain message to add
        """
        from backend.models.database import ConversationMessage

        # Convert to database format
        if isinstance(message, HumanMessage):
            role = 'user'
        elif isinstance(message, AIMessage):
            role = 'assistant'
        else:
            role = 'system'

        # Save to database
        db_message = ConversationMessage(
            conversation_id=self.conversation_id,
            role=role,
            content=message.content
        )

        self.db.add(db_message)
        self.db.commit()

        # Update cache
        self._cache.append(message)

        logger.debug(
            f"Added {role} message to conversation {self.conversation_id}: "
            f"{message.content[:50]}..."
        )

    def clear(self) -> None:
        """Clear all messages from history and database"""
        from backend.models.database import ConversationMessage

        # Delete from database
        self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == self.conversation_id
        ).delete()

        self.db.commit()

        # Clear cache
        self._cache = []
        self._loaded = True

        logger.info(f"Cleared conversation {self.conversation_id}")

    def _load_messages(self) -> None:
        """Load messages from database into cache"""
        from backend.models.database import ConversationMessage

        # Query messages
        messages = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == self.conversation_id
        ).order_by(ConversationMessage.created_at).limit(20).all()  # Last 20 messages

        # Convert to LangChain format
        self._cache = []
        for msg in messages:
            if msg.role == 'user':
                self._cache.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant':
                self._cache.append(AIMessage(content=msg.content))
            # Skip system messages for now

        self._loaded = True

        logger.debug(
            f"Loaded {len(self._cache)} messages for conversation {self.conversation_id}"
        )


class ConversationBufferMemory:
    """
    Wrapper for LangChain ConversationBufferMemory with database integration

    This provides a drop-in replacement for the current conversation_service
    """

    def __init__(self, db: Session):
        """
        Initialize conversation buffer memory

        Args:
            db: Database session
        """
        self.db = db
        self._histories: Dict[int, DatabaseChatMessageHistory] = {}

    def get_history(
        self,
        conversation_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get conversation history

        Args:
            conversation_id: Conversation ID
            limit: Number of messages to return

        Returns:
            List of message dictionaries
        """
        if conversation_id not in self._histories:
            self._histories[conversation_id] = DatabaseChatMessageHistory(
                conversation_id,
                self.db
            )

        messages = self._histories[conversation_id].messages

        # Convert to dict format
        history = []
        for msg in messages[-limit:]:
            history.append({
                'role': 'user' if isinstance(msg, HumanMessage) else 'assistant',
                'content': msg.content
            })

        return history

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str
    ) -> None:
        """
        Add a message to conversation

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
        """
        if conversation_id not in self._histories:
            self._histories[conversation_id] = DatabaseChatMessageHistory(
                conversation_id,
                self.db
            )

        # Convert to LangChain message
        if role == 'user':
            message = HumanMessage(content=content)
        else:
            message = AIMessage(content=content)

        self._histories[conversation_id].add_message(message)

    def clear_history(self, conversation_id: int) -> None:
        """
        Clear conversation history

        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self._histories:
            self._histories[conversation_id].clear()

    def get_last_n_messages(
        self,
        conversation_id: int,
        n: int = 5
    ) -> List[BaseMessage]:
        """
        Get last N messages from conversation

        Args:
            conversation_id: Conversation ID
            n: Number of messages to return

        Returns:
            List of LangChain messages
        """
        if conversation_id not in self._histories:
            self._histories[conversation_id] = DatabaseChatMessageHistory(
                conversation_id,
                self.db
            )

        messages = self._histories[conversation_id].messages
        return messages[-n:]
