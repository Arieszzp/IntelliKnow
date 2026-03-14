"""
Unified orchestrator interface with dynamic switching between original and LangChain implementations
"""
import logging
from typing import Dict, Any, Optional
from backend.config import settings

logger = logging.getLogger(__name__)


class OrchestratorInterface:
    """
    Unified interface for query orchestration
    Supports both original and LangChain implementations
    """

    def __init__(self):
        self._use_langchain = settings.use_langchain
        self._orchestrator = None

        if self._use_langchain:
            self._init_langchain()
        else:
            self._init_original()

        logger.info(f"Using {'LangChain' if self._use_langchain else 'original'} orchestrator")

    def _init_original(self):
        """Initialize original orchestrator"""
        try:
            from backend.services.orchestrator import Orchestrator
            self._orchestrator = Orchestrator()
            logger.info("Original orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize original orchestrator: {e}")
            raise

    def _init_langchain(self):
        """Initialize LangChain orchestrator"""
        try:
            from backend.services.langchain_orchestrator import LangChainOrchestrator
            self._orchestrator = LangChainOrchestrator()
            logger.info("LangChain orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain orchestrator: {e}")
            logger.warning("Falling back to original orchestrator")
            self._use_langchain = False
            self._init_original()

    def process_query(
        self,
        query: str,
        platform: str = "web",
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a query using the configured orchestrator

        Args:
            query: User query
            platform: Platform identifier (web, telegram, teams, dingtalk, feishu)
            user_id: User identifier
            conversation_id: Conversation identifier

        Returns:
            Dictionary with query results
        """
        from backend.core.database import SessionLocal

        try:
            # Both original and LangChain orchestrators need db session
            db = SessionLocal()
            try:
                return self._orchestrator.process_query(
                    query_text=query,
                    platform=platform,
                    db=db,
                    user_id=user_id
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error processing query: {e}")

            # If using LangChain and error occurs, try falling back to original
            if self._use_langchain:
                logger.warning("Error with LangChain orchestrator, attempting fallback")
                try:
                    self._use_langchain = False
                    self._init_original()
                    db = SessionLocal()
                    try:
                        return self._orchestrator.process_query(
                            query_text=query,
                            platform=platform,
                            db=db,
                            user_id=user_id
                        )
                    finally:
                        db.close()
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

            # Return error response
            return {
                "answer": "抱歉，处理您的查询时遇到错误。请稍后重试。",
                "error": str(e),
                "success": False,
                "sources": [],
                "intent": None,
                "confidence": 0.0
            }

    @property
    def is_using_langchain(self) -> bool:
        """Check if using LangChain orchestrator"""
        return self._use_langchain

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        if hasattr(self._orchestrator, 'get_stats'):
            return self._orchestrator.get_stats()
        return {
            "type": "langchain" if self._use_langchain else "original",
            "status": "active"
        }


# Global instance
orchestrator: Optional[OrchestratorInterface] = None


def get_orchestrator() -> OrchestratorInterface:
    """
    Get the global orchestrator instance
    Creates one if it doesn't exist
    """
    global orchestrator
    if orchestrator is None:
        orchestrator = OrchestratorInterface()
    return orchestrator
