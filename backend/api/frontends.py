"""
API endpoints for frontend integration management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.models.database import FrontendIntegration
from backend.models.schemas import FrontendIntegrationCreate, FrontendIntegrationUpdate, FrontendIntegrationResponse

router = APIRouter(prefix="/api/frontends", tags=["frontends"])


@router.post("/", response_model=FrontendIntegrationResponse)
def create_integration(
    integration: FrontendIntegrationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new frontend integration
    """
    existing = db.query(FrontendIntegration).filter(
        FrontendIntegration.platform == integration.platform
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Integration for this platform already exists")

    integration_db = FrontendIntegration(
        platform=integration.platform,
        is_active=integration.is_active
    )
    db.add(integration_db)
    db.commit()
    db.refresh(integration_db)

    return integration_db


@router.get("/", response_model=List[FrontendIntegrationResponse])
def list_integrations(db: Session = Depends(get_db)):
    """
    List all frontend integrations
    """
    integrations = db.query(FrontendIntegration).all()
    return integrations


@router.get("/{integration_id}", response_model=FrontendIntegrationResponse)
def get_integration(integration_id: int, db: Session = Depends(get_db)):
    """
    Get integration by ID
    """
    integration = db.query(FrontendIntegration).filter(FrontendIntegration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.put("/{integration_id}", response_model=FrontendIntegrationResponse)
def update_integration(
    integration_id: int,
    integration_update: FrontendIntegrationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update integration
    """
    integration = db.query(FrontendIntegration).filter(
        FrontendIntegration.id == integration_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    for field, value in integration_update.dict(exclude_unset=True).items():
        setattr(integration, field, value)

    db.commit()
    db.refresh(integration)
    return integration


@router.delete("/{integration_id}")
def delete_integration(integration_id: int, db: Session = Depends(get_db)):
    """
    Delete integration
    """
    integration = db.query(FrontendIntegration).filter(
        FrontendIntegration.id == integration_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    db.delete(integration)
    db.commit()

    return {"message": "Integration deleted successfully"}


@router.post("/{integration_id}/test")
def test_integration(integration_id: int, db: Session = Depends(get_db)):
    """
    Test frontend integration
    """
    integration = db.query(FrontendIntegration).filter(
        FrontendIntegration.id == integration_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        # Simulate test query
        from backend.services.orchestrator import orchestrator
        result = orchestrator.process_query(
            "Test query from integration",
            integration.platform,
            db
        )

        # Update test status
        from datetime import datetime
        integration.last_tested_at = datetime.utcnow()
        integration.test_status = "success"
        db.commit()

        return {
            "status": "success",
            "response": result['response'],
            "response_time_ms": result['response_time_ms']
        }

    except Exception as e:
        integration.test_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Integration test failed: {str(e)}")
