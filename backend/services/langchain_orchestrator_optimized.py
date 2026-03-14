"""
Optimized LangChain Orchestrator with TTFT monitoring
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path
import logging
import time

from backend.models.database import Query, QueryResult, Document, ResponseStatus
from backend.services.langchain_config import langchain_config
from backend.services.custom_retriever import FallbackRetriever
from backend.services.custom_chain import IntentSpaceAwareQAChain, MultiTurnQAChain
from backend.services.db_chat_history import ConversationBufferMemory
from backend.services.intent_classifier import intent_classifier

logger = logging.getLogger(__name__)


class LangChainOrchestrator:
    """
    LangChain-based orchestrator with optimized performance
    """

    def __init__(self):
        self.confidence_threshold = langchain_config.confidence_threshold
        self.vectorstore = None
        self.qa_chain = None
        self.memory = None
        self._initialized = False

        logger.info("LangChainOrchestrator created (optimized version)")

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

            # Initialize LLM (only for response generation, keep high quality)
            llm = Tongyi(
                dashscope_api_key=langchain_config.api_key,
                **langchain_config.get_llm_kwargs()
            )

            # Create retriever
            retriever = FallbackRetriever(
                vectorstore=self.vectorstore,
                top_k=5
            )

            # Create QA chain (without intent_classifier, we handle it separately)
            self.qa_chain = IntentSpaceAwareQAChain(
                llm=llm,
                retriever=retriever,
                intent_classifier=None  # We'll handle classification separately
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
        Process a complete query with TTFT monitoring

        Args:
            query_text: User's question
            platform: Platform name (teams, telegram, admin)
            db: Database session
            user_id: Optional user ID for multi-turn dialogue

        Returns:
            Dictionary with query results and performance metrics
        """
        start_time = time.time()
        perf_metrics = {}

        try:
            # Initialize if needed
            if not self._initialized:
                self.initialize(db)

            # Get or create conversation
            conversation = None
            if user_id:
                from backend.services.conversation_service import conversation_service as conv_service
                conversation = conv_service.get_or_create_conversation(platform, user_id, db)

            # Get conversation history
            conversation_history = []
            if conversation:
                conversation_history = self.memory.get_history(conversation.id, limit=5)

            # Add user message
            if conversation:
                self.memory.add_message(conversation.id, 'user', query_text)

            # Get intent spaces
            from backend.models.database import IntentSpace
            intent_spaces = db.query(IntentSpace).all()
            intent_spaces_list = [{
                'name': space.name,
                'description': space.description,
                'keywords': space.keywords
            } for space in intent_spaces]

            # STEP 1: Intent Classification with TTFT start
            logger.info("=" * 60)
            logger.info(f"🔍 Processing query: {query_text[:50]}...")
            logger.info("=" * 60)

            intent_start = time.time()
            # Use classify_simple for better performance (uses cached intent_spaces)
            classification = intent_classifier.classify_simple(query_text)
            intent_time_ms = int((time.time() - intent_start) * 1000)
            perf_metrics['intent_classification_ms'] = intent_time_ms
            perf_metrics['intent_cached'] = classification.get('cached', False)

            intent_space_name = classification['intent_space']
            confidence = classification['confidence']

            logger.info(f"📊 Intent: {intent_space_name} "
                       f"(confidence: {confidence:.2f}, time: {intent_time_ms}ms, "
                       f"cached: {perf_metrics['intent_cached']})")

            intent_space = db.query(IntentSpace).filter(IntentSpace.name == intent_space_name).first()

            # STEP 2: Vector Retrieval
            retrieval_start = time.time()
            docs = self.vectorstore.search(
                query_text,
                k=5,
                intent_space_id=intent_space.id if intent_space else None
            )
            retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            perf_metrics['vector_retrieval_ms'] = retrieval_time_ms

            logger.info(f"🔎 Retrieved {len(docs)} documents ({retrieval_time_ms}ms)")

            # STEP 3: Build context
            context_parts = []
            for idx, doc in enumerate(docs):
                doc_name = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', 'N/A')
                content = doc.page_content[:500]
                citation = f"[Source {idx + 1}: {doc_name}, Page {page}]"
                context_parts.append(f"{citation}\n{content}")

            context = "\n\n".join(context_parts)

            # STEP 4: Generate Response (LLM call)
            generation_start = time.time()
            first_token_time = None
            full_response = ""

            try:
                # Build prompt
                lang = 'zh' if any('\u4e00' <= c <= '\u9fff' for c in query_text) else 'en'
                if lang == 'zh':
                    system_prompt = f"""你是一个{intent_space_name if intent_space else '通用'}知识管理系统的助手。
基于提供的上下文简洁回答。

核心规则：
1. 简洁为主：控制在200字以内
2. 必须引用：每个关键信息后标注「来源：文档名」
3. 使用项目符号
4. 如果上下文有相关信息，必须基于此回答"""
                else:
                    system_prompt = f"""You are a {intent_space_name if intent_space else 'general'} knowledge assistant.
Be concise and cite sources.

Core rules:
1. Keep under 150 words
2. Cite sources with (Source: DocumentName)
3. Use bullet points
4. Answer from context if available"""

                user_prompt = f"""Context:
{context}

Question: {query_text}

Provide a clear answer based on the context."""

                # Use DashScope API directly for streaming support
                import dashscope
                response = dashscope.Generation.call(
                    model=langchain_config.llm_model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    result_format='message',
                    max_tokens=512,
                    temperature=langchain_config.temperature
                )

                if response.status_code == 200:
                    full_response = response.output.choices[0]['message']['content']
                else:
                    logger.error(f"LLM generation failed: {response.message}")
                    full_response = "抱歉，生成回答时遇到错误。"

            except Exception as e:
                logger.error(f"Error in LLM generation: {e}")
                full_response = "抱歉，生成回答时遇到错误。"

            generation_time_ms = int((time.time() - generation_start) * 1000)
            perf_metrics['response_generation_ms'] = generation_time_ms

            # TTFT = time from query start to first token
            # Since we use non-streaming here, TTFT = generation_time_ms
            # For streaming, we'd track first token arrival
            perf_metrics['ttft_ms'] = intent_time_ms + retrieval_time_ms + generation_time_ms

            logger.info(f"✅ Generated response ({generation_time_ms}ms)")
            logger.info(f"📈 TTFT: {perf_metrics['ttft_ms']}ms")
            logger.info(f"📊 Metrics: {perf_metrics}")
            logger.info("=" * 60)

            # Format for platform
            formatted_response = self.format_response_for_platform(full_response, platform)

            # Add assistant message
            if conversation and formatted_response:
                self.memory.add_message(conversation.id, 'assistant', formatted_response)

            # Prepare results data
            results_data = []
            for doc in docs:
                results_data.append({
                    'document_id': doc.metadata.get('document_id'),
                    'document_name': doc.metadata.get('source', 'Unknown'),
                    'key_sentence': doc.page_content[:150],
                    'excerpt': doc.page_content,
                    'page_number': doc.metadata.get('page', 0),
                    'relevance_score': doc.metadata.get('score', 0.0)
                })

            # Save query to database
            total_time_ms = int((time.time() - start_time) * 1000)

            query = Query(
                query_text=query_text,
                intent_space_id=intent_space.id if intent_space else None,
                confidence_score=confidence,
                platform=platform,
                response_status='success',
                response_time_ms=total_time_ms
            )
            db.add(query)
            db.flush()

            # Save query results
            if docs:
                for doc in docs:
                    doc_id = doc.metadata.get('document_id')
                    if doc_id:
                        query_result = QueryResult(
                            query_id=query.id,
                            document_id=doc_id,
                            relevance_score=doc.metadata.get('score', 0.0),
                            excerpt=doc.page_content[:500],
                            page_number=doc.metadata.get('page', 0)
                        )
                        db.add(query_result)

            db.commit()

            return {
                'query_id': query.id,
                'query_text': query_text,
                'response': formatted_response,
                'intent_space': {
                    'id': intent_space.id if intent_space else None,
                    'name': intent_space.name if intent_space else 'General',
                    'confidence': confidence
                },
                'response_status': 'success',
                'response_time_ms': total_time_ms,
                'results': results_data,
                'performance_metrics': perf_metrics,
                'created_at': query.created_at
            }

        except Exception as e:
            logger.error(f"Error processing query with LangChain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db.rollback()

            return {
                'query_id': None,
                'query_text': query_text,
                'response': "抱歉，处理您的查询时遇到错误。请稍后重试。",
                'intent_space': {
                    'id': None,
                    'name': 'General',
                    'confidence': 0.0
                },
                'response_status': 'failed',
                'response_time_ms': int((time.time() - start_time) * 1000),
                'results': [],
                'error': str(e)
            }

    def format_response_for_platform(self, response: str, platform: str) -> str:
        """
        Format response for specific platform constraints

        Args:
            response: Original response text
            platform: Platform name (teams, telegram, dingtalk, feishu, web)

        Returns:
            Formatted response
        """
        platform_configs = {
            "telegram": {
                "max_length": 3900,
                "bullet_char": "•",
            },
            "teams": {
                "max_length": 28000,
                "bullet_char": "*",
            },
            "dingtalk": {
                "max_length": 4096,
                "bullet_char": "•",
            },
            "feishu": {
                "max_length": 2000,
                "bullet_char": "•",
            },
            "web": {
                "max_length": 100000,
                "bullet_char": "•",
            }
        }

        config = platform_configs.get(platform, platform_configs["web"])

        # Format bullet points
        if config["bullet_char"] != "•":
            response = response.replace("•", config["bullet_char"])

        # Truncate if needed
        if config["max_length"] and len(response) > config["max_length"]:
            response = response[:config["max_length"]]

        return response


# Global instance
langchain_orchestrator = LangChainOrchestrator()
