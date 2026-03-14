"""
API endpoints for analytics and metrics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, timedelta

from backend.core.database import get_db
from backend.models.database import Query, Document, IntentSpace
from backend.models.schemas import AnalyticsDashboard

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
def get_dashboard_analytics(db: Session = Depends(get_db)):
    """
    Get comprehensive analytics dashboard
    """
    # Total queries
    total_queries = db.query(Query).count()

    # Total documents
    total_documents = db.query(Document).count()

    # Average response time
    avg_response_time = db.query(func.avg(Query.response_time_ms)).scalar() or 0

    # Classification accuracy (queries with confidence >= 0.7)
    high_confidence = db.query(Query).filter(Query.confidence_score >= 0.7).count()
    classification_accuracy = (high_confidence / total_queries * 100) if total_queries > 0 else 0

    # Queries by intent space
    intent_data = db.query(
        IntentSpace.name,
        func.count(Query.id).label('count')
    ).outerjoin(Query).group_by(IntentSpace.id).all()

    queries_by_intent = [
        {'intent_space': name, 'count': count or 0}
        for name, count in intent_data
    ]

    # Top documents (most accessed in query results)
    from backend.models.database import QueryResult
    top_docs = db.query(
        Document.id,
        Document.name,
        Document.file_format,
        func.count(QueryResult.id).label('access_count')
    ).join(QueryResult).group_by(Document.id).order_by(desc('access_count')).limit(10).all()

    top_documents = [
        {
            'id': doc.id,
            'name': doc.name,
            'format': doc.file_format,
            'access_count': doc.access_count
        }
        for doc in top_docs
    ]

    # Queries over time (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    time_data = db.query(
        func.date(Query.created_at).label('date'),
        func.count(Query.id).label('count')
    ).filter(Query.created_at >= seven_days_ago).group_by(func.date(Query.created_at)).all()

    queries_over_time = [
        {'date': str(date), 'count': count}
        for date, count in time_data
    ]

    return AnalyticsDashboard(
        total_queries=total_queries,
        total_documents=total_documents,
        avg_response_time=avg_response_time,
        classification_accuracy=classification_accuracy,
        queries_by_intent=queries_by_intent,
        top_documents=top_documents,
        queries_over_time=queries_over_time
    )


@router.get("/query-logs", response_model=List[dict])
def get_query_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get detailed query logs
    """
    from backend.models.database import QueryResult

    queries = db.query(Query).order_by(Query.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for q in queries:
        intent_space = db.query(IntentSpace).filter(IntentSpace.id == q.intent_space_id).first()

        # Get results
        results = db.query(QueryResult).filter(QueryResult.query_id == q.id).all()

        result.append({
            'id': q.id,
            'query_text': q.query_text,
            'intent_space': intent_space.name if intent_space else None,
            'confidence_score': q.confidence_score,
            'response_status': q.response_status,
            'platform': q.platform,
            'response_time_ms': q.response_time_ms,
            'created_at': q.created_at,
            'result_count': len(results)
        })

    return result
