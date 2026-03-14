"""
LangChain-based orchestrator for query processing
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from backend.models.database import Query, QueryResult, Document, ResponseStatus
from backend.services.langchain_config import langchain_config
from backend.services.custom_retriever import FallbackRetriever
from backend.services.custom_chain import IntentSpaceAwareQAChain, MultiTurnQAChain
from backend.services.db_chat_history import ConversationBufferMemory
from backend.services.intent_classifier import intent_classifier
import time

logger = logging.getLogger(__name__)


class LangChainOrchestrator:
    """
    LangChain-based orchestrator for query processing

    This orchestrator replaces the original orchestrator.py with LangChain components
    """

    def __init__(self):
        self.confidence_threshold = langchain_config.confidence_threshold
        self.vectorstore = None
        self.qa_chain = None
        self.memory = None
        self._initialized = False

        logger.info("LangChainOrchestrator created")

    def initialize(self, db: Session):
        """
        Initialize LangChain components

        Args:
            db: Database session
        """
        if self._initialized:
            return

        try:
            # Import LangChain components here to avoid circular imports
            from langchain_community.embeddings import DashScopeEmbeddings
            from langchain_community.llms import Tongyi
            from langchain_community.vectorstores import FAISS
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate

            # Initialize embeddings
            embeddings = DashScopeEmbeddings(
                model=langchain_config.embedding_model,
                dashscope_api_key=langchain_config.api_key
            )

            # Initialize vector store adapter
            from backend.services.langchain_vectorstore import LangChainVectorStore
            self.vectorstore = LangChainVectorStore(
                embeddings=embeddings,
                index_dir=Path(langchain_config.vector_db_dir),
                embedding_dimension=langchain_config.embedding_dimension
            )

            # Initialize intent classification LLM (lightweight, fast)
            intent_llm = Tongyi(
                dashscope_api_key=langchain_config.api_key,
                **langchain_config.get_intent_llm_kwargs()
            )

            # Initialize response generation LLM (high quality)
            llm = Tongyi(
                dashscope_api_key=langchain_config.api_key,
                **langchain_config.get_llm_kwargs()
            )

            # Create intent classifier
            intent_prompt = PromptTemplate.from_template(
                """Classify the following question into one of these intent spaces:

{intent_spaces}

Question: {query}

Return only the intent space name (e.g., "HR", "Finance", "IT", "General").
Do not include any other text or explanation."""
            )

            self.intent_classifier = LLMChain(llm=intent_llm, prompt=intent_prompt)

            # Create retriever with configurable top_k
            retriever = FallbackRetriever(
                vectorstore=self.vectorstore,
                top_k=langchain_config.retrieval_top_k
            )

            # Create QA chain
            self.qa_chain = IntentSpaceAwareQAChain(
                llm=llm,
                retriever=retriever,
                intent_classifier=self.intent_classifier
            )

            # Create multi-turn chain wrapper
            self.multi_turn_chain = MultiTurnQAChain(qa_chain=self.qa_chain)

            # Create conversation memory
            self.memory = ConversationBufferMemory(db=db)

            self._initialized = True
            logger.info("LangChainOrchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing LangChainOrchestrator: {e}")
            raise

    def process_query(
        self,
        query_text: str,
        platform: str,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Process a complete query using LangChain

        Args:
            query_text: User's question
            platform: Platform name (teams, telegram, admin)
            db: Database session
            user_id: Optional user ID for multi-turn dialogue

        Returns:
            Dictionary with query results and metadata
        """
        start_time = datetime.utcnow()

        try:
            # Initialize if needed
            if not self._initialized:
                self.initialize(db)

            # Get or create conversation
            conversation = None
            if user_id:
                from backend.services.conversation_service import conversation_service as conv_service
                conversation = conv_service.get_or_create_conversation(platform, user_id, db)

            # Get conversation history - disabled for speed optimization
            # conversation_history = []
            # if conversation:
            #     conversation_history = self.memory.get_history(conversation.id, limit=5)
            conversation_history = []  # Skip history to improve latency

            # Skip adding user message to avoid database lock issues
            # (conversation history is disabled anyway)
            # if conversation:
            #     self.memory.add_message(conversation.id, 'user', query_text)

            # Get intent spaces
            from backend.models.database import IntentSpace
            intent_spaces = db.query(IntentSpace).all()
            intent_spaces_list = [{
                'name': space.name,
                'description': space.description,
                'keywords': space.keywords
            } for space in intent_spaces]

            # Classify intent (get intent space ID for filtering)
            intent_start = time.time()
            intent_space_name = self._classify_intent(query_text, intent_spaces_list)
            intent_time = int((time.time() - intent_start) * 1000)
            intent_space = db.query(IntentSpace).filter(IntentSpace.name == intent_space_name).first()
            confidence = 0.8  # Default confidence
            logger.info(f"[PERF] Intent classification: {intent_time}ms -> {intent_space_name}")

            # Prepare chain inputs (pass pre-classified intent to avoid re-classification)
            chain_inputs = {
                'query': query_text,
                'intent_spaces': intent_spaces_list,
                'intent_space_id': intent_space.id if intent_space else None,
                'intent_space_name': intent_space.name if intent_space else 'General',
                'confidence': 0.8,  # Use default confidence from orchestrator
                'conversation_history': conversation_history
            }

            # Execute chain (use invoke instead of deprecated __call__)
            chain_start = time.time()
            chain_result = self.qa_chain.invoke(chain_inputs)
            chain_time = int((time.time() - chain_start) * 1000)
            # Note: intent classification time is separate from chain time now
            logger.info(f"[PERF] QA chain execution: {chain_time}ms (retrieval+gen)")

            # Process result
            response = chain_result.get('response', '')
            response_status = chain_result.get('response_status', 'failed')
            docs = chain_result.get('documents', [])
            confidence = chain_result.get('confidence', 0.0)

            # Log response for debugging
            logger.info(f"[DEBUG] Response from chain: status={response_status}, response_length={len(response)}, response_preview={response[:200]}")

            # Handle no match case
            if response_status == 'no_match':
                response = self._get_no_match_response(query_text)
                logger.info(f"[DEBUG] Using no_match response: {response[:200]}")

            # Format for platform
            formatted_response = self.format_response_for_platform(response, platform)
            logger.info(f"[DEBUG] Formatted response for {platform}: length={len(formatted_response)}, preview={formatted_response[:200]}")

            # Skip adding assistant message to avoid database lock issues
            # (conversation history is disabled anyway)
            # if conversation and formatted_response:
            #     self.memory.add_message(conversation.id, 'assistant', formatted_response)

            # Prepare results data
            results_data = []
            for doc in docs:
                results_data.append({
                    'document_id': doc.get('document_id'),
                    'document_name': doc.get('document_name', 'Unknown'),
                    'key_sentence': doc.get('excerpt', '')[:150],
                    'excerpt': doc.get('excerpt', ''),
                    'page_number': doc.get('page_number', 0),
                    'relevance_score': doc.get('relevance_score', 0.0)
                })

            # Save query to database
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            query = Query(
                query_text=query_text,
                intent_space_id=intent_space.id if intent_space else None,
                confidence_score=confidence,
                platform=platform,
                response_status=response_status,
                response_time_ms=response_time
            )
            db.add(query)
            db.flush()

            # Save query results
            if docs:
                for doc in docs:
                    if doc.get('document_id'):
                        query_result = QueryResult(
                            query_id=query.id,
                            document_id=doc['document_id'],
                            relevance_score=doc.get('relevance_score', 0.0),
                            excerpt=doc.get('excerpt', '')[:500],
                            page_number=doc.get('page_number', 0)
                        )
                        db.add(query_result)

            db.commit()

            logger.info(
                f"Processed query: {response_status} in {response_time}ms (intent={intent_time}ms, chain={chain_time}ms, total={intent_time+chain_time}ms)"
            )

            return {
                'success': response_status == 'success',
                'query_id': query.id,
                'query_text': query_text,
                'response': formatted_response,
                'intent_space': {
                    'id': intent_space.id if intent_space else None,
                    'name': intent_space.name if intent_space else 'General',
                    'confidence': confidence
                },
                'response_status': response_status,
                'response_time_ms': response_time,
                'results': results_data,
                'created_at': query.created_at
            }

        except Exception as e:
            logger.error(f"Error processing query with LangChain: {e}")
            db.rollback()

            # Fallback to original orchestrator if LangChain fails
            logger.warning("Falling back to original orchestrator")
            from backend.services.orchestrator import orchestrator
            return orchestrator.process_query(query_text, platform, db, user_id)

    def _classify_intent(self, query_text: str, intent_spaces: List[Dict] = None) -> str:
        """
        Classify query into intent space

        Args:
            query_text: User's question
            intent_spaces: List of available intent spaces (optional, uses cache if None)

        Returns:
            Intent space name
        """
        try:
            # Use simplified classifier with cached intent_spaces
            if intent_spaces is None:
                classification = intent_classifier.classify_simple(query_text)
            else:
                classification = intent_classifier.classify(query_text, intent_spaces)

            # Check confidence threshold
            if classification['confidence'] < self.confidence_threshold:
                logger.warning(
                    f"Low confidence ({classification['confidence']:.2f}), "
                    f"falling back to General"
                )
                return 'General'

            return classification['intent_space']

        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return 'General'

    def _get_no_match_response(self, query_text: str) -> str:
        """
        Generate no match response (bilingual)

        Args:
            query_text: Original query

        Returns:
            Formatted no match response
        """
        # Detect language
        lang = 'zh' if any('\u4e00' <= c <= '\u9fff' for c in query_text) else 'en'

        if lang == 'zh':
            return """❌ 未找到相关信息

知识库中没有关于该问题的文档。

💡 建议：
• 尝试使用不同的关键词
• 将复杂问题拆分为简单问题
• 询问具体政策或流程

📚 可查询领域：HR政策、财务指南、法律文档、公司制度"""
        else:
            return """❌ No Match Found

No documents found for this question.

💡 Suggestions:
• Try different keywords
• Break down complex questions
• Ask about specific policies or procedures

📚 Available areas: HR policies, Finance guides, Legal docs, Company policies"""

    def format_response_for_platform(self, response: str, platform: str) -> str:
        """
        Format response for specific platform constraints

        This method is preserved from the original orchestrator for compatibility

        Args:
            response: Original response text
            platform: Platform name (teams, telegram, dingtalk, feishu, web)

        Returns:
            Formatted response adapted to platform's native format
        """
        # Platform-specific format constraints
        platform_configs = {
            "telegram": {
                "max_length": 3900,
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for Telegram)",
                "supports_markdown": False,
                "supports_html": True
            },
            "teams": {
                "max_length": 28000,
                "bullet_char": "*",
                "truncate_msg": None,
                "supports_markdown": True,
                "supports_html": True
            },
            "dingtalk": {
                "max_length": 4096,
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for DingTalk)",
                "supports_markdown": False,
                "supports_html": False
            },
            "feishu": {
                "max_length": 2000,
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for Feishu)",
                "supports_markdown": True,
                "supports_html": False
            },
            "web": {
                "max_length": 100000,
                "bullet_char": "•",
                "truncate_msg": None,
                "supports_markdown": True,
                "supports_html": True
            }
        }

        config = platform_configs.get(platform, platform_configs["web"])

        # Format bullet points
        if config["bullet_char"] != "•":
            response = response.replace("•", config["bullet_char"])

        # Truncate if needed
        if config["max_length"] and len(response) > config["max_length"]:
            response = response[:config["max_length"]] + config["truncate_msg"]

        return response


# Global instance
langchain_orchestrator = LangChainOrchestrator()
