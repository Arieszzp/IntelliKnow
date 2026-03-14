"""
LangChain configuration and initialization
"""
from typing import Optional
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class LangChainConfig:
    """LangChain configuration"""

    def __init__(self):
        # LLM Configuration
        self.intent_model = settings.intent_model
        self.llm_model = settings.llm_model
        self.temperature = settings.temperature
        self.max_tokens = min(max(settings.max_tokens, 1), 8192)
        self.api_key = settings.dashscope_api_key

        # Embedding Configuration
        self.embedding_model = settings.embedding_model
        self.embedding_dimension = settings.embedding_dimension

        # Vector Store Configuration
        self.vector_db_dir = settings.vector_db_dir

        # Document Retrieval Configuration
        self.retrieval_top_k = settings.retrieval_top_k

        # Intent Classification
        self.confidence_threshold = 0.5  # Lower threshold to avoid false negatives

        logger.info(
            f"LangChainConfig initialized: "
            f"intent_model={self.intent_model}, "
            f"llm={self.llm_model}, "
            f"embedding={self.embedding_model}, "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens}, "
            f"retrieval_top_k={self.retrieval_top_k}"
        )

    def get_llm_kwargs(self) -> dict:
        """Get LLM initialization kwargs (for generation)"""
        return {
            "model": self.llm_model,
            "temperature": self.temperature,
            "max_tokens": min(self.max_tokens, 1200),  # 增加到 1200 以保证有足够空间生成答案
        }

    def get_intent_llm_kwargs(self) -> dict:
        """Get Intent LLM initialization kwargs"""
        return {
            "model": self.intent_model,
            "temperature": 0.3,  # Lower temperature for consistent classification
            "max_tokens": 100,
        }

    def get_embedding_kwargs(self) -> dict:
        """Get embedding model initialization kwargs"""
        return {
            "model": self.embedding_model,
        }


# Global config instance
langchain_config = LangChainConfig()
