"""
API endpoints for query processing
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import time
import os

from backend.core.database import get_db
from backend.models.schemas import QueryRequest, QueryResponse
from backend.services.orchestrator_wrapper import get_orchestrator

router = APIRouter(prefix="/api/queries", tags=["queries"])


@router.post("/process", response_model=QueryResponse)
def process_query(
    query_request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Process a query and return response
    """
    try:
        orchestrator_instance = get_orchestrator()
        result = orchestrator_instance.process_query(
            query_request.query_text,
            query_request.platform
        )

        # The new orchestrator already returns formatted response
        # Just return it as is
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history", response_model=List[dict])
def get_query_history(
    skip: int = 0,
    limit: int = 100,
    intent_space_id: int = None,
    platform: str = None,
    db: Session = Depends(get_db)
):
    """
    Get query history
    """
    from backend.models.database import Query, IntentSpace

    query = db.query(Query)

    if intent_space_id:
        query = query.filter(Query.intent_space_id == intent_space_id)

    if platform:
        query = query.filter(Query.platform == platform)

    queries = query.order_by(Query.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for q in queries:
        intent_space = db.query(IntentSpace).filter(IntentSpace.id == q.intent_space_id).first()
        result.append({
            'id': q.id,
            'query_text': q.query_text,
            'intent_space': intent_space.name if intent_space else None,
            'confidence_score': q.confidence_score,
            'response_status': q.response_status,
            'platform': q.platform,
            'response_time_ms': q.response_time_ms,
            'created_at': q.created_at
        })

    return result


@router.post("/process-stream")
async def process_query_stream(
    query_text: str,
    platform: str = "web",
    db: Session = Depends(get_db)
):
    """
    Process query with streaming response for better TTFT and perceived latency
    """
    async def generate():
        start_time = time.time()

        try:
            # Start event
            yield json.dumps({
                "type": "start",
                "timestamp": time.time()
            }) + "\n"

            # Step 1: Intent Classification (optimized with cache and qwen-turbo)
            intent_start = time.time()
            from backend.services.intent_classifier import intent_classifier
            from backend.models.database import IntentSpace

            intent_spaces = db.query(IntentSpace).all()
            intent_spaces_list = [{
                'name': space.name,
                'description': space.description,
                'keywords': space.keywords
            } for space in intent_spaces]

            # Use optimized classifier with caching
            intent_result = intent_classifier.classify(query_text, intent_spaces_list)
            intent_time = time.time() - intent_start

            yield json.dumps({
                "type": "intent",
                "data": {
                    "intent_space": intent_result['intent_space'],
                    "confidence": intent_result['confidence'],
                    "cached": intent_result.get('cached', False),
                    "reason": intent_result.get('reason', '')
                },
                "time_ms": int(intent_time * 1000)
            }) + "\n"

            # Step 2: Vector Retrieval
            retrieval_start = time.time()
            from backend.services.orchestrator_wrapper import get_orchestrator
            orchestrator = get_orchestrator()

            # Get intent space ID
            intent_space = db.query(IntentSpace).filter(
                IntentSpace.name == intent_result['intent_space']
            ).first()

            docs = orchestrator.vectorstore.search(
                query_text,
                k=2,  # Optimized for speed
                intent_space_id=intent_space.id if intent_space else None
            )
            retrieval_time = time.time() - retrieval_start

            # Format documents for display
            docs_data = [{
                'content': doc.page_content[:200],
                'metadata': doc.metadata
            } for doc in docs[:2]]

            yield json.dumps({
                "type": "documents",
                "data": docs_data,
                "time_ms": int(retrieval_time * 1000)
            }) + "\n"

            # Step 3: Stream Response Generation (TTFT critical point)
            generation_start = time.time()

            # Build context
            context_parts = []
            for idx, doc in enumerate(docs):
                doc_name = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', 'N/A')
                content = doc.page_content[:500]
                citation = f"[Source {idx + 1}: {doc_name}, Page {page}]"
                context_parts.append(f"{citation}\n{content}")

            context = "\n\n".join(context_parts)

            prompt = f"""Use the following context to answer the user's question. If you cannot find the answer in the context, say so clearly and politely.

Context:
{context}

Question: {query_text}

Answer:"""

            # Use DashScope streaming API
            import dashscope
            response = dashscope.Generation.call(
                model="qwen-plus",
                prompt=prompt,
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                stream=True,
                result_format='message'
            )

            token_count = 0
            first_token_time = None
            full_response = ""

            for chunk in response:
                if chunk.output and chunk.output.choices:
                    token = chunk.output.choices[0].message.content
                    if token:
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = (first_token_time - generation_start) * 1000

                            yield json.dumps({
                                "type": "ttft",
                                "time_ms": int(ttft)
                            }) + "\n"

                        yield json.dumps({
                            "type": "token",
                            "data": token
                        }) + "\n"
                        full_response += token
                        token_count += 1

            generation_time = time.time() - generation_start
            total_time = time.time() - start_time

            # Complete event
            yield json.dumps({
                "type": "complete",
                "total_time_ms": int(total_time * 1000),
                "generation_time_ms": int(generation_time * 1000),
                "token_count": token_count,
                "tokens_per_second": int(token_count / (generation_time * 1000) * 1000) if generation_time > 0 else 0
            }) + "\n"

        except Exception as e:
            import traceback
            yield json.dumps({
                "type": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
