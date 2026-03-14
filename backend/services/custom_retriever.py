"""
Custom Retriever with intent space filtering
"""
from typing import Optional, List
from langchain.schema import BaseRetriever, Document
from langchain_community.vectorstores import FAISS
import logging

logger = logging.getLogger(__name__)


class IntentSpaceFilteredRetriever(BaseRetriever):
    """
    Custom retriever that supports intent space filtering

    This retriever extends FAISS vector store to filter results by intent_space_id
    """

    def __init__(
        self,
        vectorstore: FAISS,
        intent_space_id: Optional[int] = None,
        top_k: int = 5,
        search_kwargs: Optional[dict] = None,
        **kwargs
    ):
        """
        Initialize the retriever

        Args:
            vectorstore: LangChain FAISS vector store
            intent_space_id: Optional intent space ID to filter results
            top_k: Number of results to return
            search_kwargs: Additional search parameters
        """
        super().__init__(**kwargs)
        object.__setattr__(self, 'vectorstore', vectorstore)
        object.__setattr__(self, 'intent_space_id', intent_space_id)
        object.__setattr__(self, 'top_k', top_k)
        object.__setattr__(self, 'search_kwargs', search_kwargs or {})
        logger.info(
            f"IntentSpaceFilteredRetriever initialized: "
            f"intent_space_id={intent_space_id}, top_k={top_k}"
        )

    def set_intent_space_id(self, intent_space_id: Optional[int]):
        """Update the intent space filter"""
        object.__setattr__(self, 'intent_space_id', intent_space_id)
        logger.debug(f"Intent space filter updated to: {intent_space_id}")

    def _get_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        """
        Retrieve relevant documents with intent space filtering

        Args:
            query: Search query
            run_manager: LangChain run manager

        Returns:
            List of relevant documents filtered by intent space
        """
        try:
            # Search with more results to allow for filtering
            search_k = self.top_k * 3

            # Perform similarity search (without extra kwargs)
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query,
                k=search_k
            )

            # Filter by intent space if specified
            filtered_docs = []
            for doc, score in docs_with_scores:
                # Get intent_space_id from metadata
                doc_intent_space_id = doc.metadata.get('intent_space_id')

                # Filter logic
                if self.intent_space_id is None:
                    # No filter, include all
                    should_include = True
                elif doc_intent_space_id is None:
                    # Document has no intent space, only include if we're not filtering
                    should_include = (self.intent_space_id is None)
                else:
                    # Include if matches the filter
                    should_include = (doc_intent_space_id == self.intent_space_id)

                if should_include:
                    # Add score to metadata for reference
                    doc.metadata['score'] = float(score)
                    doc.metadata['relevance'] = 'high' if score < 0.3 else 'medium' if score < 0.6 else 'low'
                    filtered_docs.append(doc)

                    # Stop if we have enough results
                    if len(filtered_docs) >= self.top_k:
                        break

            logger.info(
                f"Retrieved {len(filtered_docs)} documents for query "
                f"(intent_space_id={self.intent_space_id}), "
                f"from {len(docs_with_scores)} total matches"
            )

            return filtered_docs

        except Exception as e:
            logger.error(f"Error in intent space filtered retrieval: {e}")
            # Fallback to basic search without filtering
            return self.vectorstore.similarity_search(query, k=self.top_k)

    async def _aget_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        """
        Async version of document retrieval

        Args:
            query: Search query
            run_manager: LangChain run manager

        Returns:
            List of relevant documents
        """
        # For now, use the synchronous version
        # Can be optimized later with async vector store operations
        return self._get_relevant_documents(query, run_manager=run_manager)


class FallbackRetriever(BaseRetriever):
    """
    Retriever with fallback logic

    If no results found with intent space filter, it falls back to search all spaces
    """

    def __init__(
        self,
        vectorstore: FAISS,
        intent_space_id: Optional[int] = None,
        top_k: int = 5,
        search_kwargs: Optional[dict] = None,
        **kwargs
    ):
        """
        Initialize the fallback retriever

        Args:
            vectorstore: LangChain FAISS vector store
            intent_space_id: Primary intent space ID to filter
            top_k: Number of results to return
            search_kwargs: Additional search parameters
        """
        super().__init__(**kwargs)
        object.__setattr__(self, 'vectorstore', vectorstore)
        object.__setattr__(self, 'intent_space_id', intent_space_id)
        object.__setattr__(self, 'top_k', top_k)
        object.__setattr__(self, 'search_kwargs', search_kwargs or {})
        logger.info(
            f"FallbackRetriever initialized: "
            f"intent_space_id={intent_space_id}, top_k={top_k}"
        )

    def _get_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        """
        Retrieve with fallback to all spaces

        Args:
            query: Search query
            run_manager: LangChain run manager

        Returns:
            List of relevant documents
        """
        try:
            # First try with intent space filter
            filtered_retriever = IntentSpaceFilteredRetriever(
                vectorstore=self.vectorstore,
                intent_space_id=self.intent_space_id,
                top_k=self.top_k,
                search_kwargs=self.search_kwargs
            )

            docs = filtered_retriever._get_relevant_documents(query, run_manager=run_manager)

            # If no results and we have a filter, fallback to all spaces
            if not docs and self.intent_space_id is not None:
                logger.info(
                    f"No results in intent space {self.intent_space_id}, "
                    f"falling back to all spaces"
                )
                fallback_retriever = IntentSpaceFilteredRetriever(
                    vectorstore=self.vectorstore,
                    intent_space_id=None,  # No filter
                    top_k=self.top_k,
                    search_kwargs=self.search_kwargs
                )
                docs = fallback_retriever._get_relevant_documents(query, run_manager=run_manager)

                # Mark that results came from fallback
                for doc in docs:
                    doc.metadata['from_fallback'] = True

            return docs

        except Exception as e:
            logger.error(f"Error in fallback retrieval: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to basic search
            try:
                return self.vectorstore.similarity_search(query, k=self.top_k)
            except Exception as e2:
                logger.error(f"Error in final fallback: {e2}")
                return []

    async def _aget_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        """Async version"""
        return self._get_relevant_documents(query, run_manager=run_manager)
