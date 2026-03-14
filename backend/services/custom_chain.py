"""
Custom Chain for intent space aware QA
"""
from typing import Dict, List, Optional, Any
from langchain.chains.base import Chain
from langchain.schema import BasePromptTemplate, BaseOutputParser
from langchain.callbacks.manager import Callbacks, CallbackManagerForChainRun
from langchain.llms.base import LLM
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

# Cache for document names to avoid repeated database queries
_document_name_cache = {}


class IntentSpaceAwareQAChain(Chain):
    """
    Custom chain that integrates intent classification and retrieval

    This chain:
    1. Classifies the query into an intent space
    2. Retrieves documents using intent-aware retriever
    3. Generates response using LLM
    """

    input_key: str = "query"
    output_key: str = "response"

    def __init__(
        self,
        llm: LLM,
        retriever,
        intent_classifier: Optional['LLMChain'] = None,
        prompt_template: Optional[BasePromptTemplate] = None,
        **kwargs
    ):
        """
        Initialize the intent space aware QA chain

        Args:
            llm: Language model for response generation
            retriever: Intent space aware retriever
            intent_classifier: Chain for intent classification
            prompt_template: Template for LLM prompt
        """
        super().__init__(**kwargs)
        object.__setattr__(self, 'llm', llm)
        object.__setattr__(self, 'retriever', retriever)
        object.__setattr__(self, 'intent_classifier', intent_classifier)
        object.__setattr__(self, 'prompt_template', prompt_template or self._create_default_prompt())

        logger.info("IntentSpaceAwareQAChain initialized")

    def _create_default_prompt(self) -> PromptTemplate:
        """Create optimized default prompt template for fast response"""
        template = """Based on the provided context, answer the question. If the answer is not in the context, clearly state that.

Context:
{context}

Question: {query}

Provide a clear and concise answer:"""

        return PromptTemplate(
            template=template,
            input_variables=["context", "query"]
        )

    def _get_intent_classification(
        self,
        query: str,
        intent_spaces: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Classify query into intent space

        Args:
            query: User's question
            intent_spaces: List of available intent spaces

        Returns:
            Classification result with intent space and confidence
        """
        if not self.intent_classifier:
            # Default to first intent space if no classifier
            return {
                'intent_space': intent_spaces[0]['name'] if intent_spaces else 'General',
                'confidence': 0.5
            }

        try:
            # Format intent spaces for classification
            intent_spaces_str = "\n".join([
                f"- {space['name']}: {space.get('description', '')}"
                for space in intent_spaces
            ])

            # Use classifier - LLMChain.run() returns a string
            classification = self.intent_classifier.run(
                query=query,
                intent_spaces=intent_spaces_str
            )

            # Parse classification result - classification is a string containing the intent space name
            intent_space_name = str(classification).strip()

            # Check if it matches any known intent space
            known_spaces = [space['name'] for space in intent_spaces]
            if intent_space_name in known_spaces:
                return {
                    'intent_space': intent_space_name,
                    'confidence': 0.8  # Assume high confidence if classifier returned a valid space
                }
            else:
                # Fallback to General
                logger.warning(f"Unknown intent space '{intent_space_name}', falling back to General")
                return {
                    'intent_space': 'General',
                    'confidence': 0.5
                }

        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return {
                'intent_space': 'General',
                'confidence': 0.0
            }

    def _build_context(
        self,
        docs: List,
        query: str
    ) -> str:
        """
        Build optimized context string from retrieved documents

        Args:
            docs: Retrieved documents
            query: Original query

        Returns:
            Formatted context string
        """
        context_parts = []

        for idx, doc in enumerate(docs):
            # Get metadata
            doc_name = doc.metadata.get('source', 'Unknown Document')
            page = doc.metadata.get('page', 'N/A')
            score = doc.metadata.get('score', 0.0)
            content_type = doc.metadata.get('type', 'text')

            # Adjust content length based on type - balance between quality and speed
            if content_type == 'table':
                # Use more content for tables (tables need more context)
                content = doc.page_content[:500]
            else:
                # Use longer content for text to ensure enough information
                content = doc.page_content[:400]

            # Format citation with document info
            citation = f"Document: {doc_name} (Page {page}, Relevance: {score:.2f})"
            context_parts.append(f"{citation}\n{content}\n")

        return "\n".join(context_parts)

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: CallbackManagerForChainRun
    ) -> Dict[str, Any]:
        """
        Execute the chain

        Args:
            inputs: Chain inputs (must contain 'query')
            run_manager: Callback manager

        Returns:
            Chain outputs
        """
        query = inputs[self.input_key]
        # Skip intent classification - use pre-classified intent from orchestrator
        intent_space_id = inputs.get('intent_space_id')
        intent_space_name = inputs.get('intent_space_name', 'General')
        confidence = inputs.get('confidence', 0.8)

        logger.info(f"Processing query: {query[:50]}... (using pre-classified intent: {intent_space_name})")

        import time
        chain_start = time.time()

        try:
            # Step 1: Retrieve documents (skip intent classification)
            retrieval_start = time.time()
            # Update retriever's intent space filter
            if hasattr(self.retriever, 'set_intent_space_id'):
                self.retriever.set_intent_space_id(intent_space_id)

            # Retrieve documents
            docs = self.retriever.get_relevant_documents(query)
            retrieval_time = int((time.time() - retrieval_start) * 1000)
            logger.info(f"[PERF] Document retrieval: {retrieval_time}ms")

            if not docs:
                logger.warning(f"No documents retrieved for query")
                return {
                    self.output_key: "",
                    'intent_space': intent_space_name,
                    'confidence': confidence,
                    'documents': [],
                    'response_status': 'no_match'
                }

            # Step 2: Build context
            context = self._build_context(docs, query)

            # Step 3: Generate response
            prompt = self.prompt_template.format(
                context=context,
                query=query
            )

            logger.info(f"[DEBUG] Prompt for LLM: {prompt[:500]}...")

            generation_start = time.time()
            response = self.llm.predict(prompt)
            generation_time = int((time.time() - generation_start) * 1000)
            logger.info(f"[PERF] LLM generation: {generation_time}ms")
            logger.info(f"[DEBUG] LLM response: {response[:300]}...")

            total_time = int((time.time() - chain_start) * 1000)
            logger.info(f"[PERF] Total chain time: {total_time}ms (retrieval={retrieval_time}ms, generation={generation_time}ms)")

            # Step 5: Prepare output
            results = []
            document_ids = set()

            for doc in docs:
                doc_id = doc.metadata.get('document_id')
                if doc_id:
                    document_ids.add(doc_id)

            # Get document names from cache first (skip DB query)
            document_names = {}
            if document_ids:
                # Try to get all from cache first
                cached_names = {doc_id: _document_name_cache.get(doc_id) for doc_id in document_ids}

                # Only query DB for missing documents
                missing_ids = [doc_id for doc_id, name in cached_names.items() if name is None]

                if missing_ids:
                    try:
                        from backend.core.database import SessionLocal
                        from backend.models.database import Document

                        db = SessionLocal()
                        try:
                            documents = db.query(Document).filter(
                                Document.id.in_(missing_ids)
                            ).all()

                            for doc in documents:
                                document_names[doc.id] = doc.name
                                # Update cache
                                _document_name_cache[doc.id] = doc.name

                        finally:
                            db.close()
                    except Exception as e:
                        logger.error(f"Error fetching document names: {e}")

                # Merge cached names
                document_names.update({k: v for k, v in cached_names.items() if v is not None})

            for doc in docs:
                doc_id = doc.metadata.get('document_id')
                doc_name = document_names.get(doc_id, _document_name_cache.get(doc_id, 'Unknown Document'))

                results.append({
                    'document_id': doc_id,
                    'document_name': doc_name,
                    'page_number': doc.metadata.get('page', 0),
                    'relevance_score': doc.metadata.get('score', 0.0),
                    'excerpt': doc.page_content[:200] + "..."
                })

            return {
                self.output_key: response,
                'intent_space': intent_space_name,
                'confidence': confidence,
                'documents': results,
                'response_status': 'success',
                'context': context
            }

        except Exception as e:
            logger.error(f"Error in IntentSpaceAwareQAChain: {e}")
            return {
                self.output_key: "I apologize, but I encountered an error processing your request.",
                'intent_space': 'General',
                'confidence': 0.0,
                'documents': [],
                'response_status': 'failed',
                'error': str(e)
            }

    @property
    def _chain_type(self) -> str:
        """Return chain type identifier"""
        return "intent_space_aware_qa"

    @property
    def input_keys(self) -> List[str]:
        """Return input keys"""
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        """Return output keys"""
        return [self.output_key, 'intent_space', 'confidence', 'documents', 'response_status']


class MultiTurnQAChain(Chain):
    """
    Chain that supports multi-turn conversations with memory
    """

    input_key: str = "query"
    output_key: str = "response"

    def __init__(
        self,
        qa_chain: IntentSpaceAwareQAChain,
        **kwargs
    ):
        """
        Initialize multi-turn QA chain

        Args:
            qa_chain: Base QA chain
        """
        super().__init__(**kwargs)
        object.__setattr__(self, 'qa_chain', qa_chain)

        logger.info("MultiTurnQAChain initialized")

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: CallbackManagerForChainRun
    ) -> Dict[str, Any]:
        """
        Execute chain with conversation history

        Args:
            inputs: Chain inputs
            run_manager: Callback manager

        Returns:
            Chain outputs
        """
        query = inputs[self.input_key]
        conversation_history = inputs.get('conversation_history', [])

        # Build query with history context
        if conversation_history:
            history_context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history[-5:]  # Last 5 messages
            ])
            query = f"Conversation history:\n{history_context}\n\nCurrent question: {query}"

        # Run base QA chain
        return self.qa_chain(inputs, run_manager=run_manager)

    @property
    def _chain_type(self) -> str:
        """Return chain type identifier"""
        return "multi_turn_qa"

    @property
    def input_keys(self) -> List[str]:
        """Return input keys"""
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        """Return output keys"""
        return self.qa_chain.output_keys
