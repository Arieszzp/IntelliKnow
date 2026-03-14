"""
Feishu/Lark Bot integration
"""
import logging
import json
import os
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FeishuBot:
    """Feishu/Lark Bot handler"""

    def __init__(self):
        self.name = "Feishu/Lark"
        self._access_token: Optional[str] = None
        # Track processed events to avoid duplicates
        self._processed_events = set()
        self._max_event_cache = 1000  # Maximum number of event IDs to cache

    async def handle_webhook_get(self, query_params: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Handle Feishu webhook verification (GET request)

        Args:
            query_params: Query parameters from the request

        Returns:
            Challenge response for verification
        """
        from backend.config import settings

        # Get challenge token from query params
        challenge = query_params.get("challenge")

        if challenge and settings.feishu_verification_token:
            # Verify token
            token = query_params.get("token")
            if token == settings.feishu_verification_token:
                logger.info("Feishu webhook verification successful")
                return {"challenge": challenge}
            else:
                logger.warning("Feishu webhook verification failed: invalid token")
                return None

        return None

    async def handle_webhook_post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Feishu webhook messages (POST request)

        Args:
            body: Webhook payload from Feishu

        Returns:
            Response data in Feishu format
        """
        try:
            # Log the full request body for debugging
            logger.info(f"Feishu webhook body: {json.dumps(body, ensure_ascii=False, indent=2)[:1000]}")

            # Check if this is an event callback
            if body.get("type") == "url_verification":
                # URL verification challenge
                challenge = body.get("challenge")
                if challenge:
                    logger.info("Feishu URL verification challenge received")
                    return {"challenge": challenge}

            # Get event data and event type
            # Feishu sends event_type in header, not in event
            header = body.get("header", {})
            event_data = body.get("event", {})
            event_type = header.get("event_type")
            event_id = header.get("event_id")

            logger.info(f"Feishu event type: {event_type}, event_id: {event_id}")

            # Check for duplicate events (Feishu may retry)
            if event_id in self._processed_events:
                logger.info(f"Duplicate event {event_id}, ignoring")
                return {"code": 0, "msg": "ok"}

            # Add to processed events
            self._processed_events.add(event_id)

            # Clean up old event IDs to prevent memory issues
            if len(self._processed_events) > self._max_event_cache:
                # Remove oldest entries
                self._processed_events = set(list(self._processed_events)[-self._max_event_cache//2:])

            # Handle message events
            if event_type == "im.message.receive_v1":
                return await self._handle_message(event_data)

            return {"code": 0, "msg": "ok"}

        except Exception as e:
            logger.error(f"Error processing Feishu webhook: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"code": 500, "msg": str(e)}

    async def _handle_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Feishu message event

        Args:
            event_data: Event data from Feishu

        Returns:
            Response data
        """
        from backend.services.orchestrator_wrapper import get_orchestrator
        from backend.config import settings
        from backend.utils.response_formatter import ResponseFormatter

        message = event_data.get("message", {})
        content = message.get("content", "")

        # Parse content (it's base64 encoded)
        try:
            content_dict = json.loads(content)
            text_content = content_dict.get("text", "")
            logger.info(f"Feishu message content: {text_content[:100]}")
        except:
            text_content = content

        if not text_content:
            return {"code": 0, "msg": "ok"}

        # Get user and chat information
        sender_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id")
        chat_id = message.get("chat_id")

        logger.info(f"Processing Feishu query from user {sender_id} in chat {chat_id}")

        # Process query
        orchestrator_instance = get_orchestrator()
        result = orchestrator_instance.process_query(
            text_content,
            "feishu",
            user_id=str(sender_id) if sender_id else None
        )

        # Format response with platform-specific formatting and sources
        response_text = ResponseFormatter.format_response("feishu", result, include_sources=True)

        # Send response back to Feishu
        if chat_id and sender_id:
            feishu_response = await self.send_message(chat_id, response_text, sender_id)
            logger.info(f"Feishu response sent: {feishu_response}")

        return {"code": 0, "msg": "success"}

    async def send_message(self, chat_id: str, text: str, user_id: str) -> Dict[str, Any]:
        """
        Send message to Feishu/Lark

        Args:
            chat_id: Feishu chat ID
            text: Message text
            user_id: User open_id

        Returns:
            Response from Feishu API
        """
        from backend.config import settings

        try:
            # Get access token
            access_token = await self.get_access_token()

            if not access_token:
                logger.error("Failed to get Feishu access token")
                return {"code": -1, "msg": "No access token"}

            # Send message API
            url = "https://open.feishu.cn/open-apis/im/v1/messages"

            # Build message content
            # For p2p chat, use user_id as receive_id and set receive_id_type to "open_id"
            # For group chat, use chat_id and set receive_id_type to "chat_id"
            message_data = {
                "receive_id": user_id,  # Use user's open_id for p2p
                "msg_type": "text",
                "content": json.dumps({"text": text})
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # receive_id_type must be a query parameter, not in the body
            params = {
                "receive_id_type": "open_id"
            }

            logger.info(f"Sending Feishu message: receive_id={user_id}, receive_id_type=open_id, text={text[:100]}")

            response = requests.post(url, json=message_data, headers=headers, params=params, timeout=5)

            logger.info(f"Feishu API response: {response.status_code}, {response.text[:200]}")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Feishu API error: {response.text}")
                return {"code": response.status_code, "msg": response.text}

        except Exception as e:
            logger.error(f"Error sending Feishu message: {e}")
            return {"code": -1, "msg": str(e)}

    async def get_access_token(self) -> Optional[str]:
        """
        Get Feishu/Lark access token

        Returns:
            Access token string or None
        """
        from backend.config import settings

        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

            data = {
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    access_token = result.get("tenant_access_token")
                    logger.info("Feishu access token retrieved successfully")
                    return access_token
                else:
                    logger.error(f"Feishu token error: {result}")
                    return None
            else:
                logger.error(f"Feishu token request failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting Feishu access token: {e}")
            return None

    def health_check(self) -> Dict[str, str]:
        """
        Health check for Feishu bot

        Returns:
            Health status dict
        """
        from backend.config import settings

        return {
            "status": "healthy",
            "bot": "Feishu/Lark",
            "app_id": settings.feishu_app_id
        }


def create_feishu_bot() -> FeishuBot:
    """Factory function to create Feishu bot instance"""
    return FeishuBot()
