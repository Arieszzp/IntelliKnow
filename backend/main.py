"""
Main FastAPI application for IntelliKnow KMS
"""
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging.config import dictConfig
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file (explicitly specify path)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
print(f"[CONFIG] Loaded .env from: {env_path.absolute()}")

from backend.config import settings
from backend.core.database import init_db
from backend.api import documents, intent_spaces, queries, analytics, frontends, bots, chunks

# Configure logging
dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
})

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting IntelliKnow KMS...")
    init_db()
    logger.info("Database initialized")

    # Preload intent spaces for classification cache
    logger.info("Preloading intent spaces for classification...")
    from backend.services.intent_classifier import intent_classifier
    from backend.core.database import SessionLocal
    from backend.models.database import IntentSpace

    try:
        db = SessionLocal()
        intent_spaces = db.query(IntentSpace).all()

        intent_spaces_list = [
            {
                'id': space.id,
                'name': space.name,
                'description': space.description,
                'keywords': space.keywords
            }
            for space in intent_spaces
        ]

        # Trigger descriptions cache build
        intent_classifier._get_cached_descriptions(intent_spaces_list)
        logger.info(f"✓ Preloaded {len(intent_spaces)} intent spaces for classification")
    except Exception as e:
        logger.warning(f"Failed to preload intent spaces: {e}")
    finally:
        if 'db' in locals():
            db.close()

    yield

    # Shutdown
    logger.info("Shutting down IntelliKnow KMS...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Gen AI-powered Knowledge Management System with multi-frontend integration",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(documents.router)
app.include_router(intent_spaces.router)
app.include_router(queries.router)
app.include_router(analytics.router)
app.include_router(frontends.router)
app.include_router(bots.router)
app.include_router(chunks.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "documents": "/api/documents",
            "intent-spaces": "/api/intent-spaces",
            "queries": "/api/queries",
            "analytics": "/api/analytics",
            "frontends": "/api/frontends",
            "bots": "/api/bot",
            "chunks": "/api/chunks"
        }
    }


# Legacy webhook endpoints for DingTalk compatibility
@app.get("/webhook/dingtalk")
async def legacy_dingtalk_webhook_get(request: Request):
    """Legacy DingTalk webhook GET endpoint (for webhook verification)"""
    try:
        # DingTalk sends GET request for webhook URL verification
        # The challenge parameter needs to be echoed back
        challenge = request.query_params.get("challenge", "")
        msg = request.query_params.get("msg", "")
        token = request.query_params.get("token", "")
        nonce = request.query_params.get("nonce", "")

        if challenge:
            logging.info(f"Received DingTalk webhook verification: challenge={challenge}")
            # Echo back the challenge for verification
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=challenge, media_type="text/plain")

        # DingTalk may send other parameters for verification
        if token or nonce:
            logging.info(f"Received DingTalk webhook verification: token={token}, nonce={nonce}")
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=token if token else nonce, media_type="text/plain")

        # Simple success response for any GET request
        logging.info("Received DingTalk webhook GET request")
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"success": True, "message": "Webhook is ready"})

    except Exception as e:
        logging.error(f"Error processing DingTalk webhook GET: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/dingtalk")
async def legacy_dingtalk_webhook_post(request: Request):
    """Legacy DingTalk webhook POST endpoint (for receiving messages)"""
    try:
        body = await request.json()
        logging.info(f"Received DingTalk webhook (legacy path): {body}")

        # Process the same as the main endpoint
        from backend.services.orchestrator_wrapper import get_orchestrator
        from backend.utils.response_formatter import ResponseFormatter

        # Parse DingTalk message
        if isinstance(body, dict):
            content = body.get("text", {}).get("content", "")
        else:
            return {"status": "error", "message": "Invalid request format"}

        if content:
            orchestrator_instance = get_orchestrator()
            result = orchestrator_instance.process_query(content, "dingtalk")
            response_text = ResponseFormatter.format_response("dingtalk", result, include_sources=True)
            response_data = {
                "msgtype": "text",
                "text": {
                    "content": response_text
                }
            }
            return response_data
        else:
            return {"status": "ok"}

    except Exception as e:
        logging.error(f"Error processing DingTalk webhook (legacy): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
