"""
API endpoints for chunk management

Provides endpoints for:
1. Viewing document chunks
2. Manual chunk editing
3. Adding new chunks
4. Deleting chunks
5. Re-parsing documents
6. Semantic search within chunks
7. Chunk validation and statistics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.services.chunk_manager import chunk_manager
from backend.models.database import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chunks", tags=["chunks"])


# Pydantic models for request/response
class ChunkUpdate(BaseModel):
    """Request model for chunk update"""
    chunk_index: int
    new_text: str


class ChunkAdd(BaseModel):
    """Request model for chunk addition"""
    chunk_text: str
    chunk_type: str = 'text'
    page_number: int = 1


class ChunkResponse(BaseModel):
    """Response model for chunk"""
    index: int
    chunk_index: int
    page_number: Optional[int]
    text: str
    type: str
    score: Optional[float] = None
    intent_space_id: Optional[int] = None
    document_id: Optional[int] = None


@router.get("/document/{document_id}", response_model=List[ChunkResponse])
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all chunks for a document

    Returns:
        List of chunks with metadata
    """
    try:
        chunks = chunk_manager.get_document_chunks(document_id, db)
        return chunks

    except Exception as e:
        logger.error(f"Error getting chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/search", response_model=List[ChunkResponse])
def search_chunks(
    document_id: int,
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    Semantic search within document chunks

    Args:
        document_id: Document ID to search within
        query: Search query
        top_k: Number of results to return

    Returns:
        List of relevant chunks with relevance scores
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        results = chunk_manager.search_chunks(document_id, query, top_k, db)
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[ChunkResponse])
def search_all_chunks(
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    Global semantic search across all documents

    Args:
        query: Search query
        top_k: Number of results to return

    Returns:
        List of relevant chunks with relevance scores
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Search across all documents (pass None as document_id)
        results = chunk_manager.search_chunks(None, query, top_k, db)
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching all chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/document/{document_id}/update")
def update_chunk(
    document_id: int,
    chunk_update: ChunkUpdate,
    db: Session = Depends(get_db)
):
    """
    Manually update a chunk's content

    Args:
        document_id: Document ID
        chunk_update: Chunk update data

    Returns:
        Update result
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        result = chunk_manager.update_chunk(
            document_id,
            chunk_update.chunk_index,
            chunk_update.new_text,
            db
        )

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Update failed'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document/{document_id}/add")
def add_chunk(
    document_id: int,
    chunk_add: ChunkAdd,
    db: Session = Depends(get_db)
):
    """
    Add a new chunk to a document

    Args:
        document_id: Document ID
        chunk_add: Chunk data to add

    Returns:
        Add result
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        result = chunk_manager.add_chunk(
            document_id,
            chunk_add.chunk_text,
            chunk_add.chunk_type,
            chunk_add.page_number,
            db
        )

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Add failed'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{document_id}/chunk/{chunk_index}")
def delete_chunk(
    document_id: int,
    chunk_index: int,
    db: Session = Depends(get_db)
):
    """
    Delete a specific chunk

    Args:
        document_id: Document ID
        chunk_index: Chunk index to delete

    Returns:
        Delete result
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        result = chunk_manager.delete_chunk(document_id, chunk_index, db)

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Delete failed'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document/{document_id}/reparse")
def reparse_document(
    document_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Re-parse a document with current processing configuration

    Args:
        document_id: Document ID to re-parse
        force: Force re-parsing even if file hash matches

    Returns:
        Re-parse result
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        result = chunk_manager.reparse_document(document_id, db, force)

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Re-parse failed'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-parsing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/statistics")
def get_chunk_statistics(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get statistics about document chunks

    Returns:
        Chunk statistics
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        stats = chunk_manager.get_chunk_stats(document_id, db)
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/validate")
def validate_chunks(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Validate document chunks for errors

    Returns:
        Validation result with errors and warnings
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        validation = chunk_manager.validate_chunks(document_id, db)
        return validation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
