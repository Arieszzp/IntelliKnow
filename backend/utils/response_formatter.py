"""
Response formatter for different platforms

This module handles platform-specific response formatting including:
- Adding source information
- Truncating long responses (Telegram)
- Formatting bullet points (Teams)
- Adapting to platform constraints
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Format responses for different platforms"""

    # Platform-specific limits
    MAX_LENGTH_TELEGRAM = 4096
    MAX_LENGTH_DINGTALK = 2048
    MAX_LENGTH_FEISHU = 20000
    MAX_LENGTH_TEAMS = 28000

    @staticmethod
    def format_response(
        platform: str,
        result: Dict[str, Any],
        include_sources: bool = True
    ) -> str:
        """
        Format response for a specific platform

        Args:
            platform: Platform name (telegram, dingtalk, feishu, teams)
            result: Query result from orchestrator
            include_sources: Whether to include source information

        Returns:
            Formatted response string
        """
        response_text = result.get('response') or result.get('answer') or 'No response generated'

        # Add sources if available and requested
        sources = result.get('results', [])
        if include_sources and sources:
            sources_text = ResponseFormatter._format_sources(platform, sources)
            if sources_text:
                response_text = f"{response_text}\n\n{sources_text}"

        # Apply platform-specific truncation and formatting
        formatted = ResponseFormatter._apply_platform_format(platform, response_text)

        return formatted

    @staticmethod
    def _format_sources(platform: str, sources: List[Dict[str, Any]]) -> str:
        """
        Format source list for platform

        Args:
            platform: Platform name
            sources: List of source documents

        Returns:
            Formatted sources string
        """
        if not sources:
            return ""

        # Remove duplicates and limit to top sources
        unique_sources = []
        seen_names = set()
        for source in sources[:5]:  # Limit to top 5 sources
            doc_name = source.get('document_name', 'Unknown')
            if doc_name not in seen_names and doc_name != 'Unknown':
                unique_sources.append(source)
                seen_names.add(doc_name)

        if not unique_sources:
            return ""

        # Platform-specific source formatting
        if platform == 'telegram':
            # Telegram: Simple list
            lines = ["📚 *Sources*:"]
            for idx, source in enumerate(unique_sources, 1):
                doc_name = source.get('document_name', 'Unknown')
                page = source.get('page_number', 0)
                lines.append(f"{idx}. {doc_name}" + (f" (Page {page})" if page else ""))
            return "\n".join(lines)

        elif platform == 'dingtalk':
            # DingTalk: Markdown-style list
            lines = ["**来源**"]
            for idx, source in enumerate(unique_sources, 1):
                doc_name = source.get('document_name', 'Unknown')
                page = source.get('page_number', 0)
                lines.append(f"{idx}. {doc_name}" + (f" (第{page}页)" if page else ""))
            return "\n".join(lines)

        elif platform == 'feishu':
            # Feishu: Markdown with proper formatting
            lines = ["**参考来源**"]
            for idx, source in enumerate(unique_sources, 1):
                doc_name = source.get('document_name', 'Unknown')
                page = source.get('page_number', 0)
                lines.append(f"{idx}. {doc_name}" + (f" (第{page}页)" if page else ""))
            return "\n".join(lines)

        elif platform == 'teams':
            # Teams: Rich formatting with bullets
            lines = ["📋 **Sources**:"]
            for idx, source in enumerate(unique_sources, 1):
                doc_name = source.get('document_name', 'Unknown')
                page = source.get('page_number', 0)
                lines.append(f"  • {doc_name}" + (f" (Page {page})" if page else ""))
            return "\n".join(lines)

        else:
            # Default formatting
            lines = ["Sources:"]
            for idx, source in enumerate(unique_sources, 1):
                doc_name = source.get('document_name', 'Unknown')
                lines.append(f"{idx}. {doc_name}")
            return "\n".join(lines)

    @staticmethod
    def _apply_platform_format(platform: str, text: str) -> str:
        """
        Apply platform-specific formatting and truncation

        Args:
            platform: Platform name
            text: Text to format

        Returns:
            Formatted and possibly truncated text
        """
        # Get max length for platform
        max_length = {
            'telegram': ResponseFormatter.MAX_LENGTH_TELEGRAM,
            'dingtalk': ResponseFormatter.MAX_LENGTH_DINGTALK,
            'feishu': ResponseFormatter.MAX_LENGTH_FEISHU,
            'teams': ResponseFormatter.MAX_LENGTH_TEAMS
        }.get(platform, 10000)

        # Truncate if necessary
        if len(text) > max_length:
            logger.info(f"Truncating response for {platform}: {len(text)} -> {max_length}")
            # Truncate at sentence boundary if possible
            truncated = text[:max_length - 50]
            # Try to find last sentence ending
            for sep in ['.', '。', '\n\n', '\n']:
                if sep in truncated[-100:]:
                    truncated = truncated[:truncated.rfind(sep) + 1]
                    break
            text = truncated + "\n\n...(内容过长已截断)"

        # Platform-specific formatting
        if platform == 'telegram':
            # Convert Markdown to Telegram MarkdownV2
            # Keep it simple for now
            pass

        elif platform == 'teams':
            # Format bullet points properly for Teams
            text = ResponseFormatter._format_teams_bullets(text)

        elif platform == 'dingtalk':
            # Ensure proper Markdown for DingTalk
            text = ResponseFormatter._format_dingtalk_markdown(text)

        elif platform == 'feishu':
            # Feishu supports Markdown
            text = ResponseFormatter._format_feishu_markdown(text)

        return text

    @staticmethod
    def _format_teams_bullets(text: str) -> str:
        """
        Format bullet points for Teams

        Args:
            text: Text to format

        Returns:
            Formatted text
        """
        # Replace various bullet styles with Teams-compatible format
        import re

        # Replace numbered lists with proper numbering
        text = re.sub(r'^(\d+)\.?\s+', r'\1. ', text, flags=re.MULTILINE)

        # Replace bullet points
        text = re.sub(r'^[\-\*]\s+', '• ', text, flags=re.MULTILINE)

        # Ensure proper spacing
        text = re.sub(r'\n\n+', '\n\n', text)

        return text

    @staticmethod
    def _format_dingtalk_markdown(text: str) -> str:
        """
        Format Markdown for DingTalk

        Args:
            text: Text to format

        Returns:
            Formatted text
        """
        # DingTalk has limited Markdown support
        # Keep basic formatting but remove unsupported features

        # Replace ** with __ (bold)
        text = text.replace('**', '__')

        return text

    @staticmethod
    def _format_feishu_markdown(text: str) -> str:
        """
        Format Markdown for Feishu

        Args:
            text: Text to format

        Returns:
            Formatted text
        """
        # Feishu supports Markdown
        # Ensure proper formatting

        # Replace numbered lists if needed
        import re
        text = re.sub(r'^(\d+)\)\s+', r'\1. ', text, flags=re.MULTILINE)

        return text

    @staticmethod
    def truncate_for_platform(platform: str, text: str) -> str:
        """
        Truncate text to fit platform limits

        Args:
            platform: Platform name
            text: Text to truncate

        Returns:
            Truncated text
        """
        max_length = {
            'telegram': ResponseFormatter.MAX_LENGTH_TELEGRAM,
            'dingtalk': ResponseFormatter.MAX_LENGTH_DINGTALK,
            'feishu': ResponseFormatter.MAX_LENGTH_FEISHU,
            'teams': ResponseFormatter.MAX_LENGTH_TEAMS
        }.get(platform, 10000)

        if len(text) <= max_length:
            return text

        # Truncate intelligently
        truncated = text[:max_length - 100]

        # Try to find a good breaking point
        for sep in ['\n\n', '\n', '. ', '。', ' ']:
            if sep in truncated[-200:]:
                truncated = truncated[:truncated.rfind(sep)]
                break

        return truncated + "\n\n...(内容已截断)"
