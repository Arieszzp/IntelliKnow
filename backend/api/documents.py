"""
API endpoints for document management
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import shutil
from pathlib import Path
import logging

from backend.core.database import get_db
from backend.models.database import Document, DocumentStatus, IntentSpace
from backend.models.schemas import DocumentResponse, DocumentCreate, DocumentUpdate
from backend.services.document_processor import document_processor
from backend.services.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    name: str = Query(..., description="Document name"),
    intent_space_id: int = Query(..., description="Intent space ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a document
    """
    try:
        # Validate file extension
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['pdf', 'docx', 'xlsx']:
            raise HTTPException(status_code=400, detail="Unsupported file format. Supported: PDF, DOCX, XLSX")

        # Validate intent space
        intent_space = db.query(IntentSpace).filter(IntentSpace.id == intent_space_id).first()
        if not intent_space:
            raise HTTPException(status_code=404, detail="Intent space not found")

        # Save file (add timestamp to avoid filename conflicts)
        import time
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        timestamp = int(time.time())
        file_path = upload_dir / f"{intent_space.name}_{timestamp}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file info
        file_info = document_processor.get_file_info(str(file_path))

        # Create document record
        document = Document(
            name=name,
            filename=file.filename,
            file_path=str(file_path),
            file_format=file_ext,
            file_size=file_info['size'],
            content_hash=file_info['hash'],
            intent_space_id=intent_space_id,
            status=DocumentStatus.PROCESSED
        )
        db.add(document)
        db.flush()

        # Process document
        try:
            text, chunks = document_processor.process_document(str(file_path), file_ext)

            # Add to knowledge base
            knowledge_base.add_document(document.id, chunks, intent_space_id)

            document.status = DocumentStatus.PROCESSED
            logger.info(f"Successfully processed document: {document.name}")

        except Exception as e:
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            logger.error(f"Error processing document: {e}")

        db.commit()
        db.refresh(document)

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    intent_space_id: int = Query(None),
    status: str = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all documents with optional filtering
    """
    query = db.query(Document)

    if intent_space_id:
        query = query.filter(Document.intent_space_id == intent_space_id)

    if status:
        query = query.filter(Document.status == status)

    documents = query.offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get document by ID
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update document metadata
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update fields
    for field, value in document_update.dict(exclude_unset=True).items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Delete document
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from knowledge base
    knowledge_base.delete_document(document_id)

    # Delete file
    from pathlib import Path
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    # Delete query results that reference this document (must be done first due to foreign key constraint)
    from backend.models.database import QueryResult
    db.query(QueryResult).filter(QueryResult.document_id == document_id).delete()

    # Delete from database
    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(document_id: int, db: Session = Depends(get_db)):
    """
    Re-process a document
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from KB
    knowledge_base.delete_document(document_id)

    # Re-process
    try:
        text, chunks = document_processor.process_document(document.file_path, document.file_format)
        knowledge_base.add_document(document.id, chunks, document.intent_space_id)

        document.status = DocumentStatus.PROCESSED
        document.error_message = None
        logger.info(f"Successfully re-processed document: {document.name}")

    except Exception as e:
        document.status = DocumentStatus.ERROR
        document.error_message = str(e)
        logger.error(f"Error re-processing document: {e}")

    db.commit()
    db.refresh(document)
    return document
