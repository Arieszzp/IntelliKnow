"""
API endpoints for intent space management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import logging

from backend.core.database import get_db
from backend.models.database import IntentSpace, Document, Query
from backend.models.schemas import IntentSpaceCreate, IntentSpaceUpdate, IntentSpaceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intent-spaces", tags=["intent-spaces"])


@router.post("/", response_model=IntentSpaceResponse)
def create_intent_space(
    intent_space: IntentSpaceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new intent space
    """
    # Check if intent space already exists
    existing = db.query(IntentSpace).filter(IntentSpace.name == intent_space.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Intent space with this name already exists")

    intent_space_db = IntentSpace(**intent_space.dict())
    db.add(intent_space_db)
    db.commit()
    db.refresh(intent_space_db)

    return intent_space_db


@router.get("/", response_model=List[IntentSpaceResponse])
def list_intent_spaces(db: Session = Depends(get_db)):
    """
    List all intent spaces with statistics
    """
    intent_spaces = db.query(IntentSpace).all()

    result = []
    for space in intent_spaces:
        # Count documents
        doc_count = db.query(Document).filter(Document.intent_space_id == space.id).count()

        # Calculate classification accuracy
        queries = db.query(Query).filter(Query.intent_space_id == space.id).all()
        if queries:
            accurate = sum(1 for q in queries if q.confidence_score >= 0.7)
            accuracy = (accurate / len(queries)) * 100
        else:
            accuracy = 0.0

        result.append(IntentSpaceResponse(
            id=space.id,
            name=space.name,
            description=space.description,
            keywords=space.keywords,
            is_default=space.is_default,
            created_at=space.created_at,
            updated_at=space.updated_at,
            document_count=doc_count,
            classification_accuracy=accuracy
        ))

    return result


@router.get("/{intent_space_id}", response_model=IntentSpaceResponse)
def get_intent_space(intent_space_id: int, db: Session = Depends(get_db)):
    """
    Get intent space by ID
    """
    space = db.query(IntentSpace).filter(IntentSpace.id == intent_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Intent space not found")

    # Add statistics
    doc_count = db.query(Document).filter(Document.intent_space_id == space.id).count()
    queries = db.query(Query).filter(Query.intent_space_id == space.id).all()
    if queries:
        accurate = sum(1 for q in queries if q.confidence_score >= 0.7)
        accuracy = (accurate / len(queries)) * 100
    else:
        accuracy = 0.0

    return IntentSpaceResponse(
        id=space.id,
        name=space.name,
        description=space.description,
        keywords=space.keywords,
        is_default=space.is_default,
        created_at=space.created_at,
        updated_at=space.updated_at,
        document_count=doc_count,
        classification_accuracy=accuracy
    )


@router.put("/{intent_space_id}", response_model=IntentSpaceResponse)
def update_intent_space(
    intent_space_id: int,
    intent_space_update: IntentSpaceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update intent space with enhanced validation and cache invalidation
    """
    space = db.query(IntentSpace).filter(IntentSpace.id == intent_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Intent space not found")

    # Prevent modifying default intent spaces
    if space.is_default:
        raise HTTPException(status_code=400, detail="Cannot modify default intent spaces")

    # Get original values for logging
    old_name = space.name
    old_description = space.description
    old_keywords = space.keywords

    # Validate changes
    update_data = intent_space_update.dict(exclude_unset=True)

    # If name is being changed, check for conflicts
    if 'name' in update_data and update_data['name'] != old_name:
        existing = db.query(IntentSpace).filter(
            IntentSpace.name == update_data['name'],
            IntentSpace.id != intent_space_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Intent space with this name already exists")

    # Validate keywords format (comma-separated)
    if 'keywords' in update_data:
        keywords = update_data['keywords']
        if keywords:
            # Check format
            keyword_list = [k.strip() for k in keywords.split(',')]
            if not keyword_list:
                raise HTTPException(status_code=400, detail="Keywords cannot be empty")

            # Remove duplicates and reformat
            update_data['keywords'] = ', '.join(set(keyword_list))

    # Apply updates
    for field, value in update_data.items():
        setattr(space, field, value)

    db.commit()
    db.refresh(space)

    # Log changes
    changes = []
    if 'name' in update_data:
        changes.append(f"name: '{old_name}' → '{update_data['name']}'")
    if 'description' in update_data:
        changes.append(f"description updated")
    if 'keywords' in update_data:
        changes.append(f"keywords: '{old_keywords}' → '{update_data['keywords']}'")

    if changes:
        logger.info(f"Updated intent space {intent_space_id}: {', '.join(changes)}")

    # Invalidate intent classification cache if name or keywords changed
    if 'name' in update_data or 'keywords' in update_data:
        try:
            from backend.services.intent_classifier import intent_classifier
            intent_classifier.clear_cache()
            logger.info(f"Invalidated intent classification cache due to intent space update")
        except Exception as e:
            logger.warning(f"Failed to invalidate intent cache: {e}")

    # Return with statistics
    doc_count = db.query(Document).filter(Document.intent_space_id == space.id).count()
    queries = db.query(Query).filter(Query.intent_space_id == space.id).all()
    if queries:
        accurate = sum(1 for q in queries if q.confidence_score >= 0.7)
        accuracy = (accurate / len(queries)) * 100
    else:
        accuracy = 0.0

    return IntentSpaceResponse(
        id=space.id,
        name=space.name,
        description=space.description,
        keywords=space.keywords,
        is_default=space.is_default,
        created_at=space.created_at,
        updated_at=space.updated_at,
        document_count=doc_count,
        classification_accuracy=accuracy
    )


@router.delete("/{intent_space_id}")
def delete_intent_space(intent_space_id: int, db: Session = Depends(get_db)):
    """
    Delete intent space
    """
    space = db.query(IntentSpace).filter(IntentSpace.id == intent_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Intent space not found")

    # Prevent deleting default intent spaces
    if space.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default intent spaces")

    # Check if there are associated documents
    doc_count = db.query(Document).filter(Document.intent_space_id == intent_space_id).count()
    if doc_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete intent space with {doc_count} associated documents"
        )

    # Invalidate cache
    try:
        from backend.services.intent_classifier import intent_classifier
        intent_classifier.clear_cache()
        logger.info(f"Invalidated intent classification cache due to intent space deletion")
    except Exception as e:
        logger.warning(f"Failed to invalidate intent cache: {e}")

    db.delete(space)
    db.commit()

    return {"message": "Intent space deleted successfully"}


@router.post("/{intent_space_id}/test", response_model=dict)
def test_intent_space(
    intent_space_id: int,
    test_query: str,
    db: Session = Depends(get_db)
):
    """
    Test intent space classification

    This endpoint tests how a query would be classified,
    helping administrators validate their intent space configurations.
    """
    space = db.query(IntentSpace).filter(IntentSpace.id == intent_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Intent space not found")

    # Get all intent spaces for classification
    intent_spaces = db.query(IntentSpace).all()
    intent_spaces_list = [{
        'name': s.name,
        'description': s.description,
        'keywords': s.keywords
    } for s in intent_spaces]

    # Classify the test query
    try:
        from backend.services.intent_classifier import intent_classifier
        classification = intent_classifier.classify(test_query, intent_spaces_list)

        return {
            'query': test_query,
            'classified_intent': classification['intent_space'],
            'confidence': classification['confidence'],
            'reason': classification.get('reason', ''),
            'target_intent_space': space.name,
            'matches_target': classification['intent_space'] == space.name,
            'classification_time_ms': classification.get('time_ms', 0),
            'cached': classification.get('cached', False)
        }

    except Exception as e:
        logger.error(f"Error testing intent space: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-update", response_model=dict)
def batch_update_intent_spaces(
    updates: List[IntentSpaceUpdate],
    db: Session = Depends(get_db)
):
    """
    Batch update multiple intent spaces

    Useful for bulk changes like updating all descriptions.
    Updates are applied based on the order in the list to intent space IDs.
    """
    results = {
        'success': [],
        'failed': [],
        'total_processed': 0,
        'cache_invalidated': False
    }

    try:
        for idx, update_data in enumerate(updates):
            try:
                # Need intent_space_id in update data
                if not hasattr(update_data, 'id') or update_data.id is None:
                    results['failed'].append({
                        'index': idx,
                        'error': 'Missing id field'
                    })
                    continue

                space = db.query(IntentSpace).filter(IntentSpace.id == update_data.id).first()
                if not space:
                    results['failed'].append({
                        'index': idx,
                        'id': update_data.id,
                        'error': 'Intent space not found'
                    })
                    continue

                # Prevent modifying default intent spaces
                if space.is_default:
                    results['failed'].append({
                        'index': idx,
                        'id': update_data.id,
                        'error': 'Cannot modify default intent spaces'
                    })
                    continue

                # Validate name uniqueness if changing
                update_dict = update_data.dict(exclude_unset=True, exclude={'id'})
                if 'name' in update_dict:
                    existing = db.query(IntentSpace).filter(
                        IntentSpace.name == update_dict['name'],
                        IntentSpace.id != update_data.id
                    ).first()
                    if existing:
                        results['failed'].append({
                            'index': idx,
                            'id': update_data.id,
                            'error': 'Intent space with this name already exists'
                        })
                        continue

                # Validate keywords
                if 'keywords' in update_dict and update_dict['keywords']:
                    keyword_list = [k.strip() for k in update_dict['keywords'].split(',')]
                    if keyword_list:
                        update_dict['keywords'] = ', '.join(set(keyword_list))

                # Apply update
                for field, value in update_dict.items():
                    setattr(space, field, value)

                results['success'].append({
                    'index': idx,
                    'id': update_data.id,
                    'name': space.name
                })
                results['total_processed'] += 1

            except Exception as e:
                results['failed'].append({
                    'index': idx,
                    'id': getattr(update_data, 'id', None),
                    'error': str(e)
                })

        # Commit all changes
        if results['success']:
            db.commit()

        # Invalidate cache if any successful updates
        if results['success']:
            try:
                from backend.services.intent_classifier import intent_classifier
                intent_classifier.clear_cache()
                results['cache_invalidated'] = True
                logger.info(f"Invalidated intent classification cache after batch update")
            except Exception as e:
                logger.warning(f"Failed to invalidate intent cache: {e}")

        return results

    except Exception as e:
        db.rollback()
        logger.error(f"Error in batch update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache", response_model=dict)
def clear_intent_cache():
    """
    Clear intent classification cache

    Useful after making bulk changes to intent spaces
    to ensure the classifier uses the latest configuration.
    """
    try:
        from backend.services.intent_classifier import intent_classifier

        stats_before = intent_classifier.get_stats()
        intent_classifier.clear_cache()
        stats_after = intent_classifier.get_stats()

        return {
            'message': 'Intent classification cache cleared successfully',
            'stats_before': stats_before,
            'stats_after': stats_after
        }

    except Exception as e:
        logger.error(f"Error clearing intent cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/cache", response_model=dict)
def get_cache_stats():
    """
    Get intent classification cache statistics
    """
    try:
        from backend.services.intent_classifier import intent_classifier
        return intent_classifier.get_stats()
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
