"""
Conversation service for multi-turn dialogue and clarification
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import re

from backend.models.database import Conversation, ConversationMessage, ResponseStatus, IntentSpace

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect if text is in Chinese or English based on character analysis

    Args:
        text: Input text to analyze

    Returns:
        'zh' for Chinese, 'en' for English
    """
    # Count Chinese characters (Unicode range for CJK Unified Ideographs)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())

    if total_chars == 0:
        return 'en'

    # If more than 30% of characters are Chinese, treat as Chinese
    chinese_ratio = chinese_chars / total_chars
    if chinese_ratio > 0.3:
        logger.info(f"Detected Chinese language (ratio: {chinese_ratio:.2f})")
        return 'zh'
    else:
        logger.info(f"Detected English language (ratio: {chinese_ratio:.2f})")
        return 'en'


class ConversationService:
    """Service for managing multi-turn conversations"""

    def __init__(self):
        self.session_timeout_minutes = 30  # Sessions expire after 30 minutes

    def get_or_create_conversation(
        self,
        platform: str,
        user_id: str,
        db: Session
    ) -> Conversation:
        """
        Get existing active conversation or create new one

        Args:
            platform: Platform name (telegram, teams, admin)
            user_id: User ID from platform
            db: Database session

        Returns:
            Conversation object
        """
        # Try to find recent active conversation
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.session_timeout_minutes)

        conversation = db.query(Conversation).filter(
            Conversation.platform == platform,
            Conversation.platform_user_id == user_id,
            Conversation.is_active == True,
            Conversation.last_active_at >= cutoff_time
        ).first()

        if not conversation:
            # Create new conversation
            conversation = Conversation(
                platform=platform,
                platform_user_id=user_id,
                is_active=True
            )
            db.add(conversation)
            db.flush()
            logger.info(f"Created new conversation for {platform}:{user_id}")
        else:
            # Update last active time
            conversation.last_active_at = datetime.utcnow()
            logger.info(f"Reused conversation {conversation.id} for {platform}:{user_id}")

        return conversation

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        intent_space_id: Optional[int] = None,
        confidence_score: Optional[float] = None,
        response_status: Optional[str] = None,
        db: Session = None
    ) -> ConversationMessage:
        """
        Add a message to conversation

        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            intent_space_id: Optional intent space ID
            confidence_score: Optional classification confidence
            response_status: Optional response status
            db: Database session

        Returns:
            Created ConversationMessage object
        """
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent_space_id=intent_space_id,
            confidence_score=confidence_score,
            response_status=response_status
        )
        db.add(message)
        db.flush()
        logger.info(f"Added {role} message to conversation {conversation_id}")
        return message

    def get_conversation_history(
        self,
        conversation_id: int,
        db: Session,
        limit: int = 10
    ) -> List[ConversationMessage]:
        """
        Get conversation message history

        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages ordered by creation time
        """
        messages = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at.desc()).limit(limit).all()

        # Reverse to get chronological order
        return list(reversed(messages))

    def needs_clarification(
        self,
        query_text: str,
        confidence_score: float,
        conversation_history: List[ConversationMessage]
    ) -> bool:
        """
        Determine if query needs clarification

        This is only called when NO search results are found.

        Args:
            query_text: Current query text
            confidence_score: Classification confidence
            conversation_history: Recent conversation messages

        Returns:
            True if clarification is needed
        """
        # Don't clarify for self-introduction or general greetings
        self_intro_keywords = ['你自己', '自己', '你是谁', '你是', 'what are you', 'who are you', 'yourself', 'introduce', '介绍一下']
        query_lower = query_text.lower()
        if any(keyword in query_lower for keyword in self_intro_keywords):
            logger.info(f"Self-introduction or greeting detected, skipping clarification")
            return False

        # Don't clarify for very short greetings
        greeting_keywords = ['hello', 'hi', '你好', '您好', '嗨', 'hey']
        if any(keyword in query_lower for keyword in greeting_keywords):
            logger.info(f"Greeting detected, skipping clarification")
            return False

        # Very low confidence indicates unclear query
        if confidence_score < 0.4:
            logger.info(f"Very low confidence ({confidence_score:.2f}), query may need clarification")
            return True

        # Very short queries (less than 3 words) might be unclear
        if len(query_text.strip().split()) < 3:
            logger.info(f"Very short query ({len(query_text.strip().split())} words), may need clarification")
            return True

        # Queries that start with vague, broad terms
        vague_starters = ['what', 'how', 'tell', 'explain', 'info', 'information', 'question', 'query']
        first_word = query_text.strip().split()[0].lower() if query_text.strip().split() else ''
        if first_word in vague_starters and len(query_text.strip().split()) < 5:
            logger.info(f"Query starts with vague term '{first_word}', may need clarification")
            return True

        return False

    def generate_clarification_question(
        self,
        query_text: str,
        intent_space: Optional[str],
        db: Session
    ) -> str:
        """
        Generate a clarification question based on query and intent

        Args:
            query_text: Original query
            intent_space: Detected intent space
            db: Database session

        Returns:
            Clarification question text
        """
        # Detect language
        lang = detect_language(query_text)

        # Get available intent spaces for context
        intent_spaces = db.query(IntentSpace).all()
        intent_descriptions = "\n".join([
            f"- {space.name}: {space.description}"
            for space in intent_spaces
        ])

        if lang == 'zh':
            # Chinese clarification
            clarification = f"""我很乐意帮助您更好地了解关于「{query_text}」的信息。

能否请您进一步说明：

1. 您对哪个具体方面感兴趣？
2. 这属于哪个领域？
   {intent_descriptions}
3. 您在寻找政策、流程还是一般信息？

例如，与其问「政策是什么？」，不如尝试：
- 「年假政策是什么？」
- 「如何提交费用报销？」
- 「GDPR 合规要求有哪些？」

请提供更多详细信息，以便我给您最准确的答案。"""
        else:
            # English clarification
            clarification = f"""I'd like to help you better with "{query_text}".

Could you please clarify:
1. What specific aspect are you interested in?
2. Which area does this relate to?
   {intent_descriptions}
3. Are you looking for a policy, procedure, or general information?

For example, instead of "What's the policy?", try:
- "What's the annual leave policy?"
- "How do I submit expense reports?"
- "What are the GDPR compliance requirements?"

Please provide more details so I can give you the most accurate answer."""

        return clarification

    def close_conversation(self, conversation_id: int, db: Session):
        """
        Close a conversation

        Args:
            conversation_id: Conversation ID
            db: Database session
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if conversation:
            conversation.is_active = False
            logger.info(f"Closed conversation {conversation_id}")


# Global instance
conversation_service = ConversationService()
