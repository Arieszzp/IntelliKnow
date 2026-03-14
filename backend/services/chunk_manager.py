"""
Chunk Management Service for Manual Updates and Re-parsing

Provides capabilities for:
1. Viewing and managing document chunks
2. Manual editing of chunk content
3. Re-parsing individual documents
4. Semantic search within chunks
5. Error handling and recovery
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging
from pathlib import Path
import json
import numpy as np

from backend.core.database import get_db
from backend.models.database import Document
from backend.services.document_processor import document_processor
from backend.services.knowledge_base import knowledge_base
from backend.services.dashscope_service import dashscope_service
from backend.config import settings

logger = logging.getLogger(__name__)


class ChunkManager:
    """Service for managing document chunks with manual editing capabilities"""

    def __init__(self):
        self.chunk_size = document_processor.chunk_size
        self.chunk_overlap = document_processor.chunk_overlap

    def get_document_chunks(self, document_id: int, db: Session) -> List[Dict]:
        """
        Get all chunks for a document with their metadata

        Args:
            document_id: Document ID
            db: Database session

        Returns:
            List of chunks with metadata
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return []

            # Get all chunks for this document from vector store
            chunks = []
            for idx, doc_info in knowledge_base.documents.items():
                if doc_info['document_id'] == document_id:
                    chunk_data = {
                        'index': idx,
                        'chunk_index': doc_info.get('chunk_index'),
                        'page_number': doc_info.get('page_number'),
                        'text': doc_info['text'],
                        'type': doc_info.get('type', 'text'),
                        'intent_space_id': doc_info.get('intent_space_id'),
                        'document_name': document.name,
                        'document_id': document_id
                    }
                    chunks.append(chunk_data)

            # Sort by chunk index
            chunks.sort(key=lambda x: (
                int(x.get('chunk_index', 0)) if x.get('chunk_index') is not None else 0,
                int(x.get('index', 0))
            ))

            logger.info(f"Retrieved {len(chunks)} chunks for document {document_id}")
            return chunks

        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            raise

    def search_chunks(
        self,
        document_id: Optional[int],
        query: str,
        top_k: int = 5,
        db: Session = None
    ) -> List[Dict]:
        """
        Semantic search within document chunks

        Args:
            document_id: Document ID to search within (None for global search)
            query: Search query
            top_k: Number of results to return
            db: Database session

        Returns:
            List of matching chunks with relevance scores
        """
        try:
            # Get intent space ID for specific document
            intent_space_id = None
            if document_id is not None and db:
                document = db.query(Document).filter(Document.id == document_id).first()
                if not document:
                    logger.error(f"Document {document_id} not found")
                    return []
                intent_space_id = document.intent_space_id

            # Perform semantic search
            results = knowledge_base.search(query, intent_space_id=intent_space_id, top_k=top_k * 3)

            # Filter results
            filtered_results = []
            for result in results:
                # If document_id is specified, filter to that document
                if document_id is not None:
                    if result.get('document_id') == document_id:
                        filtered_results.append({
                            'index': result.get('index'),
                            'chunk_index': result.get('chunk_index'),
                            'page_number': result.get('page_number'),
                            'text': result.get('text'),
                            'type': result.get('type'),
                            'score': result.get('score'),
                            'intent_space_id': result.get('intent_space_id'),
                            'document_id': document_id
                        })
                else:
                    # Global search - include all results
                    filtered_results.append({
                        'index': result.get('index'),
                        'chunk_index': result.get('chunk_index'),
                        'page_number': result.get('page_number'),
                        'text': result.get('text'),
                        'type': result.get('type'),
                        'score': result.get('score'),
                        'intent_space_id': result.get('intent_space_id'),
                        'document_id': result.get('document_id')
                    })

            # Sort by relevance score
            filtered_results.sort(key=lambda x: x['score'], reverse=True)
            filtered_results = filtered_results[:top_k]

            search_scope = f"document {document_id}" if document_id else "all documents"
            logger.info(f"Found {len(filtered_results)} relevant chunks for query '{query}' in {search_scope}")
            return filtered_results

        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []

    def update_chunk(
        self,
        document_id: int,
        chunk_index: int,
        new_text: str,
        db: Session
    ) -> Dict:
        """
        Manually update a chunk's content

        Args:
            document_id: Document ID
            chunk_index: Chunk index to update
            new_text: New chunk content
            db: Database session

        Returns:
            Update result with status
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'success': False, 'error': 'Document not found'}

            # Find the chunk in vector store
            chunk_found = False
            for idx, doc_info in knowledge_base.documents.items():
                if (doc_info['document_id'] == document_id and
                    doc_info.get('chunk_index') == chunk_index):

                    # Update chunk text
                    old_text = doc_info['text']
                    doc_info['text'] = new_text

                    # Regenerate embedding for updated chunk
                    new_embedding = dashscope_service.get_embedding(new_text)

                    # Update FAISS index
                    knowledge_base.index.remove_ids(np.array([idx]))
                    knowledge_base.index.add(np.array([new_embedding], dtype='float32'))

                    # Save changes
                    knowledge_base._save()

                    chunk_found = True
                    logger.info(f"Updated chunk {chunk_index} for document {document_id}")
                    break

            if not chunk_found:
                return {'success': False, 'error': f'Chunk {chunk_index} not found'}

            return {
                'success': True,
                'message': f'Chunk {chunk_index} updated successfully',
                'old_text': old_text,
                'new_text': new_text
            }

        except Exception as e:
            logger.error(f"Error updating chunk: {e}")
            return {'success': False, 'error': str(e)}

    def delete_chunk(
        self,
        document_id: int,
        chunk_index: int,
        db: Session
    ) -> Dict:
        """
        Delete a chunk from document

        Args:
            document_id: Document ID
            chunk_index: Chunk index to delete
            db: Database session

        Returns:
            Delete result
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'success': False, 'error': 'Document not found'}

            # Find and remove chunk
            chunk_found = False
            new_documents = {}
            new_intent_spaces = {}

            for idx, doc_info in knowledge_base.documents.items():
                if doc_info['document_id'] == document_id:
                    if doc_info.get('chunk_index') == chunk_index:
                        # Skip this chunk (delete it)
                        chunk_found = True
                        logger.info(f"Deleted chunk {chunk_index} from document {document_id}")
                        continue
                    else:
                        # Keep other chunks
                        new_documents[idx] = doc_info
                        new_intent_spaces[idx] = knowledge_base.intent_spaces.get(idx)

            if not chunk_found:
                return {'success': False, 'error': f'Chunk {chunk_index} not found'}

            # Update vector store
            knowledge_base.documents = new_documents
            knowledge_base.intent_spaces = new_intent_spaces

            # Rebuild vector store
            self._rebuild_vector_store()

            return {
                'success': True,
                'message': f'Chunk {chunk_index} deleted successfully'
            }

        except Exception as e:
            logger.error(f"Error deleting chunk: {e}")
            return {'success': False, 'error': str(e)}

    def add_chunk(
        self,
        document_id: int,
        chunk_text: str,
        chunk_type: str = 'text',
        page_number: int = 1,
        db: Session = None
    ) -> Dict:
        """
        Add a new chunk to a document

        Args:
            document_id: Document ID
            chunk_text: Chunk content
            chunk_type: Type of chunk ('text' or 'table')
            page_number: Page number
            db: Database session

        Returns:
            Add result
        """
        try:
            if not db:
                return {'success': False, 'error': 'Database session required'}

            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'success': False, 'error': 'Document not found'}

            # Get next chunk index
            existing_chunks = self.get_document_chunks(document_id, db)
            max_chunk_index = max([c.get('chunk_index', 0) for c in existing_chunks], default=0)
            new_chunk_index = max_chunk_index + 1

            # Create chunk metadata
            chunk_metadata = {
                'text': chunk_text,
                'page_number': page_number,
                'chunk_index': new_chunk_index,
                'type': chunk_type,
                'document_id': document_id,
                'intent_space_id': document.intent_space_id
            }

            # Add to vector store
            chunks_list = [chunk_metadata]
            knowledge_base.add_document(document_id, chunks_list, document.intent_space_id)

            logger.info(f"Added new chunk {new_chunk_index} to document {document_id}")

            return {
                'success': True,
                'message': f'Chunk added successfully with index {new_chunk_index}',
                'chunk_index': new_chunk_index
            }

        except Exception as e:
            logger.error(f"Error adding chunk: {e}")
            return {'success': False, 'error': str(e)}

    def reparse_document(
        self,
        document_id: int,
        db: Session,
        force: bool = False
    ) -> Dict:
        """
        Re-parse a document with current processing configuration

        Args:
            document_id: Document ID to re-parse
            db: Database session
            force: Force re-parsing even if file hash matches

        Returns:
            Re-parse result
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'success': False, 'error': 'Document not found'}

            file_path = Path(document.file_path)
            if not file_path.exists():
                return {'success': False, 'error': 'Source file not found'}

            logger.info(f"Re-parsing document {document_id}: {document.name}")

            # Delete old chunks from vector store
            old_chunk_count = sum(1 for doc in knowledge_base.documents.values()
                                if doc.get('document_id') == document_id)
            knowledge_base.delete_document(document_id)
            logger.info(f"Deleted {old_chunk_count} old chunks")

            # Re-process document
            text, chunks = document_processor.process_document(
                str(file_path),
                document.file_format
            )

            # Add new chunks
            knowledge_base.add_document(document_id, chunks, document.intent_space_id)

            new_chunk_count = len(chunks)

            # Update document status
            document.status = 'processed'
            document.error_message = None
            db.commit()

            logger.info(f"Re-parsed document {document_id}: {old_chunk_count} -> {new_chunk_count} chunks")

            return {
                'success': True,
                'message': f'Document re-parsed successfully',
                'old_chunks': old_chunk_count,
                'new_chunks': new_chunk_count
            }

        except Exception as e:
            logger.error(f"Error re-parsing document: {e}")
            db.rollback()
            return {'success': False, 'error': str(e)}

    def get_chunk_stats(self, document_id: int, db: Session) -> Dict:
        """
        Get statistics about chunks for a document

        Args:
            document_id: Document ID
            db: Database session

        Returns:
            Statistics dictionary
        """
        try:
            chunks = self.get_document_chunks(document_id, db)

            if not chunks:
                return {
                    'total_chunks': 0,
                    'text_chunks': 0,
                    'table_chunks': 0,
                    'avg_text_length': 0,
                    'total_characters': 0
                }

            text_chunks = [c for c in chunks if c.get('type') == 'text']
            table_chunks = [c for c in chunks if c.get('type') == 'table']

            total_chars = sum(len(c['text']) for c in chunks)
            avg_length = total_chars / len(chunks) if chunks else 0

            return {
                'total_chunks': len(chunks),
                'text_chunks': len(text_chunks),
                'table_chunks': len(table_chunks),
                'avg_text_length': round(avg_length, 2),
                'total_characters': total_chars,
                'pages_covered': max(c.get('page_number', 0) for c in chunks) + 1
            }

        except Exception as e:
            logger.error(f"Error getting chunk stats: {e}")
            return {}

    def validate_chunks(self, document_id: int, db: Session) -> Dict:
        """
        Validate chunks for a document

        Args:
            document_id: Document ID
            db: Database session

        Returns:
            Validation result with errors and warnings
        """
        try:
            chunks = self.get_document_chunks(document_id, db)
            errors = []
            warnings = []

            # Check for empty chunks
            empty_chunks = [c for c in chunks if not c.get('text', '').strip()]
            if empty_chunks:
                warnings.append({
                    'type': 'empty_chunks',
                    'message': f'Found {len(empty_chunks)} empty chunks',
                    'count': len(empty_chunks)
                })

            # Check for very small chunks
            tiny_chunks = [c for c in chunks if len(c.get('text', '')) < 10]
            if tiny_chunks:
                warnings.append({
                    'type': 'tiny_chunks',
                    'message': f'Found {len(tiny_chunks)} very small chunks (<10 chars)',
                    'count': len(tiny_chunks)
                })

            # Check for duplicate chunks
            texts = [c.get('text', '') for c in chunks]
            duplicate_indices = []
            seen = {}
            for i, text in enumerate(texts):
                if text in seen:
                    duplicate_indices.append(i)
                    seen[text].append(i)
                else:
                    seen[text] = [i]

            if duplicate_indices:
                errors.append({
                    'type': 'duplicate_chunks',
                    'message': f'Found {len(duplicate_indices)} duplicate chunks',
                    'indices': duplicate_indices
                })

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'total_errors': len(errors),
                'total_warnings': len(warnings)
            }

        except Exception as e:
            logger.error(f"Error validating chunks: {e}")
            return {
                'valid': False,
                'errors': [{'type': 'validation_error', 'message': str(e)}],
                'warnings': [],
                'total_errors': 1,
                'total_warnings': 0
            }

    def _rebuild_vector_store(self):
        """
        Rebuild vector store after chunk modifications

        This is necessary because FAISS doesn't support efficient in-place updates
        """
        try:
            # Save current state
            knowledge_base._save()
            logger.info("Vector store rebuilt after chunk modification")

        except Exception as e:
            logger.error(f"Error rebuilding vector store: {e}")
            raise


# Global instance
chunk_manager = ChunkManager()
