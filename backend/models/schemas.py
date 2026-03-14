"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    ERROR = "error"


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NO_MATCH = "no_match"


# Intent Space Models
class IntentSpaceBase(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: Optional[str] = None


class IntentSpaceCreate(IntentSpaceBase):
    pass


class IntentSpaceUpdate(BaseModel):
    id: Optional[int] = None  # Optional, required only for batch updates
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None


class IntentSpaceResponse(IntentSpaceBase):
    id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    classification_accuracy: float = 0.0

    class Config:
        from_attributes = True


# Document Models
class DocumentBase(BaseModel):
    name: str
    intent_space_id: int


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    intent_space_id: Optional[int] = None


class DocumentResponse(DocumentBase):
    id: int
    filename: str
    file_format: str
    file_size: int
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    intent_space: Optional[IntentSpaceResponse] = None

    class Config:
        from_attributes = True


# Query Models
class QueryRequest(BaseModel):
    query_text: str
    platform: str = "admin"


class QueryResponse(BaseModel):
    id: int
    query_text: str
    intent_space: Optional[IntentSpaceResponse] = None
    confidence_score: float
    response_status: ResponseStatus
    response: Optional[str] = None
    response_time_ms: int
    created_at: datetime
    results: List[dict] = []

    class Config:
        from_attributes = True


# Frontend Integration Models
class FrontendIntegrationBase(BaseModel):
    platform: str  # teams, telegram, dingtalk
    is_active: bool = True


class FrontendIntegrationCreate(FrontendIntegrationBase):
    pass


class FrontendIntegrationUpdate(BaseModel):
    is_active: Optional[bool] = None


class FrontendIntegrationResponse(FrontendIntegrationBase):
    id: int
    last_tested_at: Optional[datetime] = None
    test_status: Optional[str] = "not_tested"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Bot Message Models
class BotMessage(BaseModel):
    platform: str
    user_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BotResponse(BaseModel):
    response: str
    intent_space: Optional[str] = None
    confidence: float
    sources: List[dict] = []


# Analytics Models
class AnalyticsDashboard(BaseModel):
    total_queries: int
    total_documents: int
    avg_response_time: float
    classification_accuracy: float
    queries_by_intent: List[dict]
    top_documents: List[dict]
    queries_over_time: List[dict]


class QueryLog(BaseModel):
    id: int
    query_text: str
    intent_space: Optional[str]
    confidence_score: float
    response_status: ResponseStatus
    platform: str
    response_time_ms: int
    created_at: datetime
