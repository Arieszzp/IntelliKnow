"""
Database session and initialization
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
from backend.models.database import Base, IntentSpace
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with default data"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create default intent spaces
        db = SessionLocal()
        
        default_intents = [
            {
                "name": "HR",
                "description": "Human Resources policies, benefits, leaves, employee handbook",
                "keywords": "hr,human resources,policy,leave,benefit,employee,handbook,payroll,recruitment,onboarding,training,performance,compensation,insurance,health,retirement,pension",
                "is_default": True
            },
            {
                "name": "Legal",
                "description": "Legal documents, contracts, compliance, regulations",
                "keywords": "legal,contract,compliance,regulation,law,agreement,terms,conditions,liability,ip,intellectual property,privacy,gdpr,audit,risk,terms of service,nda",
                "is_default": True
            },
            {
                "name": "Finance",
                "description": "Financial policies, expense reports, budgets, accounting",
                "keywords": "finance,accounting,budget,expense,report,invoice,payment,reimbursement,tax,audit,financial,policy,procurement,purchasing,cost,revenue,profit,loss,forecast",
                "is_default": True
            },
            {
                "name": "General",
                "description": "General company information, announcements, misc",
                "keywords": "general,company,announcement,news,faq,help,support,contact,about,team,mission,vision,values,organization,structure",
                "is_default": True
            }
        ]
        
        for intent_data in default_intents:
            existing = db.query(IntentSpace).filter(IntentSpace.name == intent_data["name"]).first()
            if not existing:
                intent = IntentSpace(**intent_data)
                db.add(intent)
        
        db.commit()
        logger.info("Database initialized successfully with default intent spaces")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
