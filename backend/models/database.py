"""
Database models for IntelliKnow KMS
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    ERROR = "error"


class ResponseStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NO_MATCH = "no_match"
    NEED_CLARIFICATION = "need_clarification"


class IntentSpace(Base):
    __tablename__ = "intent_spaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    keywords = Column(Text)  # Comma-separated keywords
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="intent_space")
    queries = relationship("Query", back_populates="intent_space")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_format = Column(String(10), nullable=False)
    file_size = Column(Integer)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    content_hash = Column(String(64))
    intent_space_id = Column(Integer, ForeignKey("intent_spaces.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    error_message = Column(Text)

    # Relationships
    intent_space = relationship("IntentSpace", back_populates="documents")
    query_results = relationship("QueryResult", back_populates="document")


class FrontendIntegration(Base):
    __tablename__ = "frontend_integrations"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), unique=True, nullable=False)  # teams, telegram, dingtalk
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime)
    test_status = Column(String(20), default="not_tested")  # success, failed, not_tested
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Multi-turn conversation session"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)  # telegram, teams, admin
    platform_user_id = Column(String(255), nullable=False)  # User ID from platform
    intent_space_id = Column(Integer, ForeignKey("intent_spaces.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    intent_space = relationship("IntentSpace")
    messages = relationship("ConversationMessage", back_populates="conversation")


class ConversationMessage(Base):
    """Individual message in a conversation"""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    intent_space_id = Column(Integer, ForeignKey("intent_spaces.id"))
    confidence_score = Column(Float)
    response_status = Column(SQLEnum(ResponseStatus))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    query = relationship("Query", back_populates="message")
    query_results = relationship("QueryResult", back_populates="message")


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    intent_space_id = Column(Integer, ForeignKey("intent_spaces.id"))
    confidence_score = Column(Float)
    platform = Column(String(50))  # telegram, teams, admin
    response_status = Column(SQLEnum(ResponseStatus))
    response_time_ms = Column(Integer)  # Response time in milliseconds
    message_id = Column(Integer, ForeignKey("conversation_messages.id"))  # Link to conversation
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intent_space = relationship("IntentSpace", back_populates="queries")
    results = relationship("QueryResult", back_populates="query")
    message = relationship("ConversationMessage", back_populates="query")


class QueryResult(Base):
    __tablename__ = "query_results"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    relevance_score = Column(Float)
    excerpt = Column(Text)
    page_number = Column(Integer)
    message_id = Column(Integer, ForeignKey("conversation_messages.id"))  # Link to conversation message

    # Relationships
    query = relationship("Query", back_populates="results")
    document = relationship("Document", back_populates="query_results")
    message = relationship("ConversationMessage", back_populates="query_results")
