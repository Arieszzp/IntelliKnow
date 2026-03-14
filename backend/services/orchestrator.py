"""
Orchestrator service for query classification and routing
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from backend.models.database import Query, QueryResult, Document, ResponseStatus
from backend.services.dashscope_service import dashscope_service
from backend.services.knowledge_base import knowledge_base
from backend.services.conversation_service import conversation_service

logger = logging.getLogger(__name__)


class Orchestrator:
    """Service for orchestrating query processing and routing"""

    def __init__(self):
        self.confidence_threshold = 0.7  # Default threshold from config

    def classify_query(
        self,
        query_text: str,
        intent_spaces: List[Dict],
        db: Session
    ) -> Dict:
        """
        Classify query into intent space

        Args:
            query_text: User's question
            intent_spaces: List of available intent spaces
            db: Database session

        Returns:
            Dictionary with classification results
        """
        try:
            # Use DashScope for classification
            classification = dashscope_service.classify_intent(query_text, intent_spaces)

            # Get intent space from database
            from backend.models.database import IntentSpace

            # Check confidence threshold: AI-driven if >= 70%, fallback to General
            if classification['confidence'] < self.confidence_threshold:
                logger.warning(f"Low confidence ({classification['confidence']:.2f}), falling back to General")
                intent_space = db.query(IntentSpace).filter(IntentSpace.name == "General").first()
                return {
                    'intent_space': intent_space,
                    'intent_space_name': 'General',
                    'confidence': classification['confidence']
                }

            # High confidence - use AI classification
            intent_space = db.query(IntentSpace).filter(
                IntentSpace.name == classification['intent_space']
            ).first()

            # If intent space not found, fallback to General
            if not intent_space:
                logger.warning(f"Intent space '{classification['intent_space']}' not found, falling back to General")
                intent_space = db.query(IntentSpace).filter(IntentSpace.name == "General").first()

            result = {
                'intent_space': intent_space,
                'intent_space_name': intent_space.name if intent_space else 'General',
                'confidence': classification['confidence']
            }

            logger.info(f"Classified query: {query_text[:50]}... -> {result['intent_space_name']} ({classification['confidence']:.2f})")
            return result

        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Fallback to General
            from backend.models.database import IntentSpace
            general_space = db.query(IntentSpace).filter(IntentSpace.name == "General").first()
            return {
                'intent_space': general_space,
                'intent_space_name': 'General',
                'confidence': 0.0
            }

    def process_query(
        self,
        query_text: str,
        platform: str,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Process a complete query: classify, search, generate response

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
            # Get or create conversation
            conversation = None
            if user_id:
                conversation = conversation_service.get_or_create_conversation(platform, user_id, db)

            # Get conversation history if conversation exists
            conversation_history = []
            if conversation:
                conversation_history = conversation_service.get_conversation_history(conversation.id, db, limit=5)

            # Add user message to conversation
            if conversation:
                conversation_service.add_message(
                    conversation_id=conversation.id,
                    role='user',
                    content=query_text,
                    db=db
                )

            # Get all intent spaces
            from backend.models.database import IntentSpace
            intent_spaces = db.query(IntentSpace).all()
            intent_spaces_list = [{
                'name': ispace.name,
                'description': ispace.description,
                'keywords': ispace.keywords
            } for ispace in intent_spaces]

            # Step 1: Classify intent
            classification = self.classify_query(query_text, intent_spaces_list, db)
            intent_space = classification['intent_space']
            confidence = classification['confidence']

            # Step 2: Search knowledge base (try classified intent space first)
            search_results = knowledge_base.search(
                query_text,
                intent_space_id=intent_space.id if intent_space else None,
                top_k=5
            )

            # If no results in classified intent space, search across all spaces
            if not search_results:
                logger.info(f"No results in classified intent space {intent_space.name}, searching across all spaces")
                search_results = knowledge_base.search(
                    query_text,
                    intent_space_id=None,  # No filter
                    top_k=5
                )

            # Step 3: Build context from search results with enhanced citation format
            context = ""
            results_data = []

            if search_results:
                for idx, result in enumerate(search_results[:3]):  # Use top 3 results
                    # Get document info
                    doc = db.query(Document).filter(Document.id == result['document_id']).first()
                    doc_name = doc.name if doc else "Unknown"

                    # Check if result is from a table - provide more complete content for tables
                    if result.get('type') == 'table':
                        # For tables, use more of the content (up to 500 chars)
                        key_content = result['text'][:500]
                    else:
                        # For regular text, use first 300 chars for better context
                        key_content = result['text'][:300]

                    # Enhanced citation format: [Source N: DocumentName] Content
                    context += f"\n[Source {idx + 1}: {doc_name}]\n{key_content}\n"

                    results_data.append({
                        'document_id': result['document_id'],
                        'document_name': doc_name,
                        'key_sentence': key_content[:150],  # Short version for citation display
                        'excerpt': result['text'][:200] + "...",
                        'page_number': result['page_number'],
                        'relevance_score': result['score']
                    })

            # Step 4: Check if clarification is needed (only when NO search results found)
            if not search_results and conversation_service.needs_clarification(query_text, confidence, conversation_history):
                clarification = conversation_service.generate_clarification_question(
                    query_text,
                    intent_space.name if intent_space else None,
                    db
                )

                # Add assistant message to conversation
                if conversation:
                    conversation_service.add_message(
                        conversation_id=conversation.id,
                        role='assistant',
                        content=clarification,
                        intent_space_id=intent_space.id if intent_space else None,
                        confidence_score=confidence,
                        response_status=ResponseStatus.NEED_CLARIFICATION,
                        db=db
                    )

                # Format clarification for platform
                formatted_clarification = self.format_response_for_platform(clarification, platform)

                return {
                    'query_text': query_text,
                    'response': formatted_clarification,
                    'intent_space': {
                        'name': intent_space.name if intent_space else 'General',
                        'confidence': confidence
                    },
                    'response_status': 'need_clarification',
                    'response_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    'results': []
                }

            # Step 5: Generate response
            if search_results:
                # Check if results came from a different intent space
                results_from_different_space = False
                for result in search_results[:1]:  # Check first result
                    doc = db.query(Document).filter(Document.id == result['document_id']).first()
                    if doc and doc.intent_space_id != (intent_space.id if intent_space else None):
                        results_from_different_space = True
                        break

                intent_for_llm = intent_space.name if intent_space else "General"
                if results_from_different_space:
                    # Find which intent space the results came from
                    doc = db.query(Document).filter(Document.id == search_results[0]['document_id']).first()
                    if doc:
                        from backend.models.database import IntentSpace
                        result_intent = db.query(IntentSpace).filter(IntentSpace.id == doc.intent_space_id).first()
                        if result_intent:
                            context = f"[Note: Found relevant information in {result_intent.name} documents]\n" + context

                response = dashscope_service.generate_response(
                    query_text,
                    context,
                    intent_space=intent_for_llm
                )
                response_status = "success"

                # Format response for platform before saving
                formatted_response = self.format_response_for_platform(response, platform)

                # Add assistant message to conversation
                if conversation:
                    assistant_message = conversation_service.add_message(
                        conversation_id=conversation.id,
                        role='assistant',
                        content=formatted_response,
                        intent_space_id=intent_space.id if intent_space else None,
                        confidence_score=confidence,
                        response_status=ResponseStatus.SUCCESS,
                        db=db
                    )
            else:
                # 清晰简洁的无匹配提示 - 双语支持
                lang = 'zh' if any('\u4e00' <= c <= '\u9fff' for c in query_text) else 'en'

                if lang == 'zh':
                    no_match_response = """❌ 未找到相关信息

知识库中没有关于该问题的文档。

💡 建议：
• 尝试使用不同的关键词
• 将复杂问题拆分为简单问题
• 询问具体政策或流程

📚 可查询领域：HR政策、财务指南、法律文档、公司制度"""
                else:
                    no_match_response = """❌ No Match Found

No documents found for this question.

💡 Suggestions:
• Try different keywords
• Break down complex questions
• Ask about specific policies or procedures

📚 Available areas: HR policies, Finance guides, Legal docs, Company policies"""

                # Format no-match response for platform
                formatted_no_match = self.format_response_for_platform(no_match_response, platform)
                response = formatted_no_match
                response_status = "no_match"

            # Calculate response time
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Step 5: Save query to database
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
            if search_results:
                for result in search_results:
                    query_result = QueryResult(
                        query_id=query.id,
                        document_id=result['document_id'],
                        relevance_score=result['score'],
                        excerpt=result['text'][:500],
                        page_number=result['page_number']
                    )
                    db.add(query_result)

            db.commit()

            logger.info(f"Processed query: {response_status} in {response_time}ms")

            return {
                'query_id': query.id,
                'query_text': query_text,
                'response': formatted_response if response_status == "success" else formatted_no_match if response_status == "no_match" else response,
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
            logger.error(f"Error processing query: {e}")
            db.rollback()

            return {
                'query_text': query_text,
                'response': "I apologize, but I encountered an error processing your request. Please try again later.",
                'intent_space': {'name': 'General', 'confidence': 0.0},
                'response_status': 'failed',
                'response_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                'results': [],
                'error': str(e)
            }

    def format_response_for_platform(self, response: str, platform: str) -> str:
        """
        Format response for specific platform constraints using AI-driven adaptation

        This leverages AI to adapt responses to native format constraints of each frontend tool
        without building custom formatters for each tool, streamlining integration development.

        Args:
            response: Original response text
            platform: Platform name (teams, telegram, dingtalk, feishu, web)

        Returns:
            Formatted response adapted to platform's native format
        """
        # Platform-specific format constraints
        platform_configs = {
            "telegram": {
                "max_length": 3900,  # ~4096 limit with buffer
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for Telegram)",
                "supports_markdown": False,  # Limited Markdown support
                "supports_html": True
            },
            "teams": {
                "max_length": 28000,  # Teams allows ~28K characters
                "bullet_char": "*",  # Teams uses * for bullets in Adaptive Cards
                "truncate_msg": None,  # Rarely truncates
                "supports_markdown": True,  # Full Markdown support
                "supports_html": True
            },
            "dingtalk": {
                "max_length": 4096,  # DingTalk limit
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for DingTalk)",
                "supports_markdown": False,
                "supports_html": False
            },
            "feishu": {
                "max_length": 2000,  # Feishu limit
                "bullet_char": "•",
                "truncate_msg": "\n\n... (truncated for Feishu)",
                "supports_markdown": True,  # Feishu supports some Markdown
                "supports_html": False
            },
            "web": {
                "max_length": 100000,  # Effectively unlimited
                "bullet_char": "•",
                "truncate_msg": None,
                "supports_markdown": True,
                "supports_html": True
            }
        }

        config = platform_configs.get(platform, platform_configs["web"])

        # Format bullet points for platform
        if config["bullet_char"] != "•":
            # Convert • to platform-specific bullet character
            response = response.replace("•", config["bullet_char"])

        # Truncate if exceeds platform limit
        if config["max_length"] and len(response) > config["max_length"]:
            response = response[:config["max_length"]] + config["truncate_msg"]

        # Platform-specific optimizations
        if platform == "teams":
            # Teams Adaptive Cards format optimization
            # Preserve citation format (Source: DocumentName)
            # Ensure clean rendering of bullets
            response = response.replace("\n\n", "\n")  # Reduce excessive spacing
            # Keep Markdown bold and list formats intact

        elif platform == "telegram":
            # Telegram plain text optimization
            # Citation format: (来源：文档名) is already fine for Telegram
            # Just ensure no HTML/markdown conflicts
            pass

        elif platform == "feishu":
            # Feishu/Lark optimization
            # Feishu supports basic Markdown
            # Clean up excessive line breaks
            response = response.replace("\n\n\n", "\n\n")
            # Ensure emoji compatibility
            pass

        return response


# Global instance
orchestrator = Orchestrator()
