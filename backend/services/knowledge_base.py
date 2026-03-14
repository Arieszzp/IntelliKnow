"""
Knowledge Base service for vector storage and retrieval using FAISS
"""
import faiss
import numpy as np
import pickle
from typing import List, Dict, Tuple
from pathlib import Path
import logging
from datetime import datetime

from backend.config import settings
from backend.services.dashscope_service import dashscope_service
from backend.services.document_processor import document_processor

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Service for managing knowledge base with FAISS"""

    def __init__(self):
        self.index_dir = Path(settings.vector_db_dir)
        self.embedding_dimension = settings.embedding_dimension
        self.index = None
        self.documents = {}  # Maps index to document info
        self.intent_spaces = {}  # Maps index to intent space ID

        # Initialize or load index
        self._initialize()

    def _initialize(self):
        """Initialize FAISS index or load existing"""
        try:
            index_file = self.index_dir / "faiss.index"
            docs_file = self.index_dir / "documents.pkl"

            if index_file.exists() and docs_file.exists():
                # Load existing index
                self.index = faiss.read_index(str(index_file))

                with open(docs_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.intent_spaces = data['intent_spaces']

                logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatL2(self.embedding_dimension)
                logger.info("Created new FAISS index")

        except Exception as e:
            logger.error(f"Error initializing FAISS index: {e}")
            self.index = faiss.IndexFlatL2(self.embedding_dimension)

    def _save(self):
        """Save FAISS index and metadata"""
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)

            # Save index
            faiss.write_index(self.index, str(self.index_dir / "faiss.index"))

            # Save metadata
            with open(self.index_dir / "documents.pkl", 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'intent_spaces': self.intent_spaces
                }, f)

            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")

    def add_document(
        self,
        document_id: int,
        chunks: List[Dict],
        intent_space_id: int
    ) -> int:
        """
        Add document chunks to knowledge base

        Args:
            document_id: Database document ID
            chunks: List of text chunks with metadata
            intent_space_id: Intent space ID for this document

        Returns:
            Number of vectors added
        """
        try:
            # Extract texts
            texts = [chunk['text'] for chunk in chunks]

            # Generate embeddings
            embeddings = dashscope_service.get_embeddings_batch(texts)

            # Convert to numpy array
            vectors = np.array(embeddings, dtype='float32')

            # Add to FAISS index
            start_idx = self.index.ntotal
            self.index.add(vectors)

            # Store metadata
            for i, chunk in enumerate(chunks):
                idx = start_idx + i
                self.documents[idx] = {
                    'document_id': document_id,
                    'chunk_index': chunk.get('chunk_index', i),
                    'page_number': chunk.get('page_number', 0),
                    'text': chunk['text'],
                    'type': chunk.get('type', 'text')
                }
                self.intent_spaces[idx] = intent_space_id

            # Save to disk
            self._save()

            logger.info(f"Added {len(chunks)} vectors for document {document_id}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error adding document to KB: {e}")
            raise

    def search(
        self,
        query: str,
        intent_space_id: int = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search knowledge base for relevant documents

        Args:
            query: Search query text
            intent_space_id: Optional intent space filter
            top_k: Number of results to return

        Returns:
            List of relevant chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = dashscope_service.get_embedding(query)
            query_vector = np.array([query_embedding], dtype='float32')

            # Search FAISS index
            distances, indices = self.index.search(query_vector, top_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # Invalid index
                    continue

                # Check intent space filter
                if intent_space_id and self.intent_spaces.get(idx) != intent_space_id:
                    continue

                # Get document info
                doc_info = self.documents.get(idx, {})
                if doc_info:
                    results.append({
                        'index': int(idx),  # FAISS index
                        'document_id': doc_info['document_id'],
                        'chunk_index': doc_info['chunk_index'],
                        'page_number': doc_info['page_number'],
                        'text': doc_info['text'],
                        'type': doc_info.get('type', 'text'),
                        'score': float(dist),  # L2 distance (lower is better)
                        'intent_space_id': doc_info.get('intent_space_id')
                    })

            # Sort by score (ascending for L2 distance)
            results.sort(key=lambda x: x['score'])

            logger.info(f"Found {len(results)} results for query")
            return results

        except Exception as e:
            logger.error(f"Error searching KB: {e}")
            return []

    def delete_document(self, document_id: int) -> bool:
        """
        Delete all chunks for a document from KB
        Note: FAISS doesn't support deletion efficiently, so we rebuild index

        Args:
            document_id: Document ID to delete

        Returns:
            True if successful
        """
        try:
            # Filter out chunks belonging to this document
            new_documents = {}
            new_intent_spaces = {}

            for idx, doc_info in self.documents.items():
                if doc_info['document_id'] != document_id:
                    new_documents[idx] = doc_info
                    new_intent_spaces[idx] = self.intent_spaces[idx]

            # Rebuild index
            self.documents = new_documents
            self.intent_spaces = new_intent_spaces
            self.index = faiss.IndexFlatL2(self.embedding_dimension)

            # Re-add all remaining vectors
            if new_documents:
                texts = [doc['text'] for doc in new_documents.values()]
                embeddings = dashscope_service.get_embeddings_batch(texts)
                vectors = np.array(embeddings, dtype='float32')
                self.index.add(vectors)

            # Save
            self._save()

            logger.info(f"Deleted document {document_id} from KB")
            return True

        except Exception as e:
            logger.error(f"Error deleting document from KB: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get knowledge base statistics

        Returns:
            Dictionary with KB stats
        """
        document_ids = set(doc['document_id'] for doc in self.documents.values())

        return {
            'total_chunks': len(self.documents),
            'total_documents': len(document_ids),
            'intent_space_distribution': {}
        }


# Global instance
knowledge_base = KnowledgeBase()
