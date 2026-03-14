"""
API endpoints for bot integrations (webhook handlers)
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
import logging

from backend.bots.teams_bot import create_teams_bot
from backend.bots.telegram_bot import create_telegram_bot
from backend.bots.dingtalk_bot import create_dingtalk_bot
from backend.bots.feishu_bot import create_feishu_bot
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bot", tags=["bots"])

# Create bot instances
teams_bot = create_teams_bot()
telegram_bot = create_telegram_bot(settings.telegram_bot_token)
dingtalk_bot = create_dingtalk_bot()
feishu_bot = create_feishu_bot()


@router.post("/teams/webhook")
async def teams_webhook(request: Request):
    """
    Microsoft Teams Bot webhook endpoint
    This endpoint receives messages from Microsoft Teams via Bot Framework
    """
    try:
        body = await request.json()
        logger.info(f"Received Teams webhook: {body}")
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing Teams webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams/health")
async def teams_health():
    """
    Health check for Teams bot
    """
    return teams_bot.health_check()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram Bot webhook endpoint
    This endpoint receives updates from Telegram
    """
    try:
        body = await request.json()
        logger.info(f"Received Telegram webhook: {body}")

        # Parse Telegram message format
        # Telegram sends updates with message structure
        if isinstance(body, dict):
            message = body.get("message", {})

            # Handle /start command
            text = message.get("text", "").strip()

            if text == "/start":
                # Send welcome message
                welcome_msg = "👋 Welcome to IntelliKnow KMS!\n\nI can help you find information from our knowledge base.\n\nJust ask me any question about HR, Finance, Legal, or company policies."

                # Use Telegram Bot API to send message
                chat_id = message.get("chat", {}).get("id")

                if chat_id:
                    import requests
                    bot_token = settings.telegram_bot_token
                    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    requests.post(telegram_url, json={
                        "chat_id": chat_id,
                        "text": welcome_msg
                    })
                    logger.info(f"Sent welcome message to chat_id: {chat_id}")

                return {"status": "ok"}

            elif text and len(text) > 0:
                # Process query
                from backend.services.orchestrator_wrapper import get_orchestrator
                from backend.core.database import SessionLocal

                orchestrator_instance = get_orchestrator()
                db = SessionLocal()
                try:
                    chat_id = message.get("chat", {}).get("id")
                    user_id = message.get("from", {}).get("id")

                    if chat_id:
                        import requests
                        bot_token = settings.telegram_bot_token
                        sent_message_id = None

                        try:
                            # Send initial "thinking" message
                            telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            initial_response = requests.post(telegram_url, json={
                                "chat_id": chat_id,
                                "text": "🤔 Thinking...",
                                "parse_mode": "Markdown"
                            }, timeout=10)
                            sent_message_id = initial_response.json().get("result", {}).get("message_id")
                            logger.info(f"Sent thinking message to chat_id: {chat_id}, message_id: {sent_message_id}")
                        except Exception as e:
                            logger.error(f"Failed to send thinking message: {e}")

                        try:
                            # Process query with user_id for conversation support
                            # Note: New orchestrator doesn't require db parameter
                            result = orchestrator_instance.process_query(
                                text,
                                "telegram",
                                user_id=str(user_id) if user_id else None
                            )
                            logger.info(f"Query processed, success: {result.get('success')}")

                            # Format response for Telegram
                            # Try multiple possible keys for backward compatibility
                            response_text = result.get('response') or result.get('answer') or 'No response generated'

                            # Update message with actual response
                            if sent_message_id:
                                edit_url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
                                edit_response = requests.post(edit_url, json={
                                    "chat_id": chat_id,
                                    "message_id": sent_message_id,
                                    "text": response_text,
                                    "parse_mode": "Markdown"
                                }, timeout=10)

                                if edit_response.status_code != 200:
                                    logger.error(f"Failed to edit message: {edit_response.text}")
                                else:
                                    logger.info(f"Updated message for chat_id: {chat_id}, success: {result.get('success')}")

                        except Exception as e:
                            logger.error(f"Error processing query or updating message: {e}")
                            # Try to update with error message
                            if sent_message_id:
                                try:
                                    edit_url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
                                    requests.post(edit_url, json={
                                        "chat_id": chat_id,
                                        "message_id": sent_message_id,
                                        "text": f"❌ Error: {str(e)[:200]}"
                                    }, timeout=10)
                                except Exception as edit_error:
                                    logger.error(f"Failed to send error message: {edit_error}")

                    return {"status": "ok"}

                finally:
                    db.close()

        # Return ok for webhook acknowledgement
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telegram/health")
async def telegram_health():
    """
    Health check for Telegram bot
    """
    return telegram_bot.health_check()


@router.post("/dingtalk/webhook")
async def dingtalk_webhook(request: Request):
    """
    DingTalk Bot webhook endpoint
    This endpoint receives messages from DingTalk via chatbot
    """
    try:
        body = await request.json()
        logger.info(f"Received DingTalk webhook: {body}")

        # Delegate to DingTalk bot handler
        response = await dingtalk_bot.handle_webhook(body)
        return response

    except Exception as e:
        logger.error(f"Error processing DingTalk webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dingtalk/health")
async def dingtalk_health():
    """
    Health check for DingTalk bot
    """
    return dingtalk_bot.health_check()


@router.get("/feishu/webhook")
async def feishu_webhook_get(request: Request):
    """
    Feishu/Lark webhook verification endpoint (GET request)
    Feishu sends a GET request to verify the webhook URL
    """
    # Delegate to Feishu bot handler
    query_params = dict(request.query_params)
    response = await feishu_bot.handle_webhook_get(query_params)

    if response:
        return response
    else:
        return JSONResponse(status_code=401, content={"error": "Invalid verification"})


@router.post("/feishu/webhook")
async def feishu_webhook_post(request: Request):
    """
    Feishu/Lark Bot webhook endpoint (POST request)
    This endpoint receives messages from Feishu/Lark
    """
    try:
        body = await request.json()
        logger.info(f"Received Feishu webhook")

        # Delegate to Feishu bot handler
        response = await feishu_bot.handle_webhook_post(body)
        return response

    except Exception as e:
        logger.error(f"Error processing Feishu webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"code": 500, "msg": str(e)}


@router.get("/feishu/health")
async def feishu_health():
    """
    Health check for Feishu bot
    """
    return feishu_bot.health_check()


@router.post("/test/query")
async def test_query(request: Request):
    """
    Test endpoint for querying the system
    """
    try:
        body = await request.json()
        query_text = body.get("query", "")
        platform = body.get("platform", "admin")

        if not query_text:
            raise HTTPException(status_code=400, detail="Query text is required")

        # Process query
        from backend.services.orchestrator_wrapper import get_orchestrator

        orchestrator_instance = get_orchestrator()
        result = orchestrator_instance.process_query(query_text, platform)
        return result

    except Exception as e:
        logger.error(f"Error in test query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
