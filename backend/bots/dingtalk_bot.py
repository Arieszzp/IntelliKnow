"""
DingTalk Bot integration
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DingTalkBot:
    """DingTalk Bot handler"""

    def __init__(self):
        self.name = "DingTalk"

    async def handle_webhook(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle DingTalk webhook messages

        Args:
            body: Webhook payload from DingTalk

        Returns:
            Response data in DingTalk format
        """
        try:
            from backend.services.orchestrator_wrapper import get_orchestrator
            from backend.utils.response_formatter import ResponseFormatter

            # Parse DingTalk message format
            content = body.get("text", {}).get("content", "")

            if not content:
                return {"msgtype": "text", "text": {"content": "请提供问题"}}

            # Process query
            orchestrator_instance = get_orchestrator()
            result = orchestrator_instance.process_query(content, "dingtalk")

            # Format response with platform-specific formatting and sources
            response_text = ResponseFormatter.format_response("dingtalk", result, include_sources=True)

            return {
                "msgtype": "text",
                "text": {
                    "content": response_text
                }
            }

        except Exception as e:
            logger.error(f"Error in DingTalk bot: {e}")
            return {
                "msgtype": "text",
                "text": {"content": f"Error: {str(e)[:200]}"}
            }

    def health_check(self) -> Dict[str, str]:
        """
        Health check for DingTalk bot

        Returns:
            Health status dict
        """
        return {
            "status": "healthy",
            "bot": "DingTalk"
        }


def create_dingtalk_bot() -> DingTalkBot:
    """Factory function to create DingTalk bot instance"""
    return DingTalkBot()
