"""
LangChain VectorStore adapter for existing FAISS index
"""
import faiss
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any
from langchain_community.vectorstores import FAISS as LangChainFAISS
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LangChainVectorStore:
    """
    Adapter for LangChain vector store using existing FAISS index

    This class wraps the existing FAISS index to work with LangChain's
    vector store interface while maintaining compatibility with current data
    """

    def __init__(
        self,
        embeddings: Embeddings,
        index_dir: Path,
        embedding_dimension: int = 1024,
        force_rebuild: bool = False
    ):
        """
        Initialize LangChain vector store adapter

        Args:
            embeddings: LangChain embeddings instance
            index_dir: Directory containing FAISS index
            embedding_dimension: Dimension of embeddings
            force_rebuild: Force rebuild even if index exists (for debugging)
        """
        self.embeddings = embeddings
        self.index_dir = index_dir
        self.embedding_dimension = embedding_dimension
        self.langchain_store: Optional[LangChainFAISS] = None
        self.documents = {}  # Maps index to document info
        self.intent_spaces = {}  # Maps index to intent space ID
        self.force_rebuild = force_rebuild

        # Initialize or load
        self._initialize()

        logger.info(
            f"LangChainVectorStore initialized with {self._get_vector_count()} vectors"
        )

    def _initialize(self):
        """Initialize FAISS index or load existing"""
        try:
            index_file = self.index_dir.joinpath("faiss.index")
            docs_file = self.index_dir.joinpath("documents.pkl")
            lc_store_file = self.index_dir.joinpath("langchain_store.pkl")

            if index_file.exists() and docs_file.exists():
                # Load existing index
                faiss_index = faiss.read_index(str(index_file))

                # Load metadata
                with open(docs_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', {})
                    self.intent_spaces = data.get('intent_spaces', {})

                logger.info(f"Loaded existing FAISS index with {faiss_index.ntotal} vectors")
                logger.info(f"Loaded {len(self.documents)} documents from metadata")

                # Check if LangChain store cache exists and is valid
                if not self.force_rebuild and self._try_load_cached_store(lc_store_file):
                    return

                # Rebuild LangChain store from scratch to ensure consistency
                # This is safer than trying to reuse the existing index
                self._rebuild_langchain_store()

            else:
                # Create new index
                faiss_index = faiss.IndexFlatL2(self.embedding_dimension)
                logger.info("Created new FAISS index")

                # Create LangChain store
                self.langchain_store = LangChainFAISS(
                    embedding_function=self.embeddings,
                    index=faiss_index
                )

        except Exception as e:
            logger.error(f"Error initializing LangChain vector store: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Create new index as fallback
            import numpy as np
            new_index = faiss.IndexFlatL2(self.embedding_dimension)
            from langchain.docstore import InMemoryDocstore
            self.langchain_store = LangChainFAISS(
                embedding_function=self.embeddings,
                index=new_index,
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={}
            )

    def _try_load_cached_store(self, lc_store_file: Path) -> bool:
        """
        Try to load cached LangChain store

        Args:
            lc_store_file: Path to cached store file

        Returns:
            True if successfully loaded, False otherwise
        """
        if not lc_store_file.exists():
            return False

        try:
            with open(lc_store_file, 'rb') as f:
                data = pickle.load(f)

            # Verify cache validity
            cached_doc_count = data.get('document_count', 0)
            current_doc_count = len(self.documents)

            if cached_doc_count != current_doc_count:
                logger.info(
                    f"Cache mismatch: cached {cached_doc_count} docs, "
                    f"current {current_doc_count} docs. Rebuilding..."
                )
                return False

            # Load cached LangChain store
            self.langchain_store = data['langchain_store']
            logger.info("Loaded cached LangChain store")
            return True

        except Exception as e:
            logger.warning(f"Failed to load cached store: {e}. Will rebuild.")
            return False

    def _save_cached_store(self, lc_store_file: Path):
        """
        Save LangChain store to cache

        Args:
            lc_store_file: Path to cache file
        """
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)

            with open(lc_store_file, 'wb') as f:
                pickle.dump({
                    'langchain_store': self.langchain_store,
                    'document_count': len(self.documents),
                    'timestamp': datetime.utcnow().isoformat()
                }, f)

            logger.info("Saved LangChain store to cache")

        except Exception as e:
            logger.warning(f"Failed to save cached store: {e}")

    def _create_docstore(self):
        """
        Create LangChain docstore from our documents dict

        Returns:
            Dictionary-based docstore
        """
        from langchain.docstore import InMemoryDocstore

        # Convert to LangChain Documents
        docs_dict = {}
        for idx, doc_info in self.documents.items():
            doc = Document(
                page_content=doc_info['text'],
                metadata={
                    'document_id': doc_info['document_id'],
                    'chunk_index': doc_info.get('chunk_index', idx),
                    'page_number': doc_info.get('page_number', 0),
                    'type': doc_info.get('type', 'text'),
                    'intent_space_id': self.intent_spaces.get(idx),
                    'source': f"doc_{doc_info['document_id']}"
                }
            )
            docs_dict[str(idx)] = doc

        return InMemoryDocstore(docs_dict)

    def _create_index_mapping(self, total_indices: int):
        """
        Create index to docstore ID mapping

        Args:
            total_indices: Total number of indices in FAISS

        Returns:
            Dictionary mapping index IDs to docstore IDs
        """
        # Create mapping for all indices, even those without document metadata
        mapping = {}
        for idx in range(total_indices):
            mapping[str(idx)] = str(idx)
        return mapping

    def _rebuild_langchain_store(self):
        """Rebuild LangChain store from documents metadata"""
        logger.info("Rebuilding LangChain store from metadata...")

        # Reconstruct all documents and vectors
        if not self.documents:
            # No documents, create empty store
            new_index = faiss.IndexFlatL2(self.embedding_dimension)
            from langchain.docstore import InMemoryDocstore
            self.langchain_store = LangChainFAISS(
                embedding_function=self.embeddings,
                index=new_index,
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={}
            )
            return

        # Prepare texts and metadatas
        texts = []
        metadatas = []

        for idx in sorted(self.documents.keys()):
            doc_info = self.documents[idx]
            texts.append(doc_info['text'])
            metadatas.append({
                'document_id': doc_info['document_id'],
                'chunk_index': doc_info.get('chunk_index', idx),
                'page_number': doc_info.get('page_number', 0),
                'type': doc_info.get('type', 'text'),
                'intent_space_id': self.intent_spaces.get(idx),
                'source': f"doc_{doc_info['document_id']}"
            })

        # Create new LangChain store with batching (max 10 per batch)
        if texts:
            logger.info(f"Re-embedding {len(texts)} documents...")
            batch_size = 10
            all_embeddings = []

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1} with {len(batch_texts)} documents...")
                batch_embeddings = self.embeddings.embed_documents(batch_texts)
                all_embeddings.extend(batch_embeddings)

            # Create FAISS index
            import numpy as np
            new_index = faiss.IndexFlatL2(self.embedding_dimension)
            new_index.add(np.array(all_embeddings, dtype=np.float32))

            # Create docstore - IMPORTANT: use integer keys to match FAISS indices
            from langchain.docstore import InMemoryDocstore
            docs_dict = {i: self._create_langchain_doc(texts[i], metadatas[i]) for i in range(len(texts))}
            docstore = InMemoryDocstore(docs_dict)

            # Create index mapping - IMPORTANT: use integer keys
            index_mapping = {i: i for i in range(len(texts))}

            # Create LangChain store
            self.langchain_store = LangChainFAISS(
                embedding_function=self.embeddings,
                index=new_index,
                docstore=docstore,
                index_to_docstore_id=index_mapping
            )
            logger.info(f"Rebuilt LangChain store with {self.langchain_store.index.ntotal} vectors")

            # Save to cache for next time
            lc_store_file = self.index_dir.joinpath("langchain_store.pkl")
            self._save_cached_store(lc_store_file)
        else:
            # Empty store
            new_index = faiss.IndexFlatL2(self.embedding_dimension)
            from langchain.docstore import InMemoryDocstore
            self.langchain_store = LangChainFAISS(
                embedding_function=self.embeddings,
                index=new_index,
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={}
            )

    def _create_langchain_doc(self, text: str, metadata: dict):
        """Create LangChain Document"""
        return Document(page_content=text, metadata=metadata)

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        document_id: int,
        intent_space_id: int
    ) -> int:
        """
        Add documents to vector store

        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts
            document_id: Document database ID
            intent_space_id: Intent space ID

        Returns:
            Number of vectors added
        """
        try:
            # Add to LangChain store
            self.langchain_store.add_texts(texts, metadatas)

            # Update our metadata
            start_idx = len(self.documents)
            for i, (text, meta) in enumerate(zip(texts, metadatas)):
                idx = start_idx + i
                self.documents[idx] = {
                    'document_id': document_id,
                    'chunk_index': i,
                    'page_number': meta.get('page_number', 0),
                    'text': text,
                    'type': meta.get('type', 'text')
                }
                self.intent_spaces[idx] = intent_space_id

            # Save to disk
            self._save()

            logger.info(f"Added {len(texts)} vectors for document {document_id}")
            return len(texts)

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise

    def search(
        self,
        query: str,
        k: int = 5,
        intent_space_id: Optional[int] = None
    ) -> List[Document]:
        """
        Search vector store

        Args:
            query: Search query
            k: Number of results to return
            intent_space_id: Optional intent space filter

        Returns:
            List of relevant documents
        """
        try:
            # Use LangChain store for search
            results = self.langchain_store.similarity_search_with_score(query, k=k * 3)

            # Filter by intent space if specified
            filtered_results = []
            for doc, score in results:
                doc_intent_space_id = doc.metadata.get('intent_space_id')

                if intent_space_id is None:
                    # No filter
                    should_include = True
                elif doc_intent_space_id is None:
                    should_include = (intent_space_id is None)
                else:
                    should_include = (doc_intent_space_id == intent_space_id)

                if should_include:
                    # Add score to metadata
                    doc.metadata['score'] = float(score)
                    filtered_results.append((doc, score))

                    if len(filtered_results) >= k:
                        break

            # Sort by score and return documents
            filtered_results.sort(key=lambda x: x[1])
            return [doc for doc, score in filtered_results]

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def delete_document(self, document_id: int) -> bool:
        """
        Delete all vectors for a document

        Note: FAISS doesn't support efficient deletion, so we rebuild

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

            # Rebuild LangChain store
            from langchain.docstore import InMemoryDocstore
            self.langchain_store = LangChainFAISS(
                embedding_function=self.embeddings,
                index=faiss.IndexFlatL2(self.embedding_dimension),
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={}
            )

            # Re-add all remaining vectors
            if new_documents:
                texts = [doc['text'] for doc in new_documents.values()]
                metadatas = [
                    {
                        'document_id': doc['document_id'],
                        'chunk_index': doc['chunk_index'],
                        'page_number': doc['page_number'],
                        'type': doc['type'],
                        'intent_space_id': self.intent_spaces[idx]
                    }
                    for idx, doc in new_documents.items()
                ]

                self.langchain_store.add_texts(texts, metadatas)

            # Save
            self._save()

            logger.info(f"Deleted document {document_id} from vector store")
            return True

        except Exception as e:
            logger.error(f"Error deleting document from vector store: {e}")
            return False

    def _save(self):
        """Save FAISS index and metadata"""
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)

            # Save index
            faiss.write_index(
                self.langchain_store.index,
                str(self.index_dir.joinpath("faiss.index"))
            )

            # Save metadata
            with open(self.index_dir.joinpath("documents.pkl"), 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'intent_spaces': self.intent_spaces
                }, f)

            # Invalidate cached LangChain store since documents changed
            lc_store_file = self.index_dir.joinpath("langchain_store.pkl")
            if lc_store_file.exists():
                lc_store_file.unlink()
                logger.info("Invalidated cached LangChain store (documents changed)")

            logger.info(
                f"Saved FAISS index with {self._get_vector_count()} vectors"
            )

        except Exception as e:
            logger.error(f"Error saving vector store: {e}")

    def _get_vector_count(self) -> int:
        """Get total number of vectors in the store"""
        return len(self.documents)

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        document_ids = set(doc['document_id'] for doc in self.documents.values())
        intent_space_counts = {}

        for intent_space_id in self.intent_spaces.values():
            if intent_space_id is not None:
                intent_space_counts[intent_space_id] = intent_space_counts.get(intent_space_id, 0) + 1

        return {
            'total_chunks': len(self.documents),
            'total_documents': len(document_ids),
            'intent_space_distribution': intent_space_counts
        }

    @property
    def retriever(self):
        """Get retriever interface"""
        return self.langchain_store.as_retriever()

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Perform similarity search

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of similar documents
        """
        return self.langchain_store.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """
        Perform similarity search with scores

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        return self.langchain_store.similarity_search_with_score(query, k=k)
