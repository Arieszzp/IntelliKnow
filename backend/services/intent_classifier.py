"""
Optimized Intent Classifier with caching and lightweight LLM
"""
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import logging

import dashscope
from dashscope import Generation

from backend.config import settings

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    High-performance intent classifier with caching and lightweight LLM
    """

    def __init__(self):
        # Use lightweight model for classification (2-3x faster)
        # Model can be configured via INTENT_MODEL env variable
        self.classification_model = settings.intent_model
        self.generation_model = settings.llm_model  # Keep high quality for generation

        # Confidence threshold
        self.confidence_threshold = 0.6

        logger.info(
            f"IntentClassifier models: "
            f"classification={self.classification_model}, "
            f"generation={self.generation_model}"
        )

        # In-memory cache with TTL
        self._cache = {}
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour

        # Cache for intent descriptions (avoid rebuilding on every call)
        self._intent_descriptions_cache = ""
        self._last_intent_spaces_hash = None

        # Global intent spaces cache (avoid DB query on every classification)
        self._intent_spaces_cache = None
        self._intent_spaces_cache_time = None
        self._intent_spaces_cache_ttl = timedelta(minutes=5)  # Refresh every 5 minutes

        # Stats tracking
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'llm_calls': 0,
            'avg_llm_time_ms': 0,
            'descriptions_cache_hits': 0,
            'intent_spaces_cache_hits': 0
        }

        logger.info(f"IntentClassifier initialized with {self.classification_model} (classification), {self.generation_model} (generation)")

    def _classify_by_keywords(
        self,
        query: str,
        intent_spaces: List[Dict]
    ) -> Optional[Dict[str, any]]:
        """
        Fast keyword-based classification (no LLM call)

        Args:
            query: User's question
            intent_spaces: List of available intent spaces

        Returns:
            Classification result if confident, None if needs LLM
        """
        query_lower = query.lower()

        # Count keyword matches for each intent space
        intent_scores = []
        for space in intent_spaces:
            keywords = space.get('keywords', [])
            if isinstance(keywords, str):
                keywords = [kw.strip().lower() for kw in keywords.split(',') if kw.strip()]

            # Count matches
            matches = 0
            matched_keywords = []
            for kw in keywords:
                if kw in query_lower:
                    matches += 1
                    matched_keywords.append(kw)

            if matches > 0:
                # Calculate confidence based on match count
                confidence = min(0.5 + (matches * 0.15), 0.95)
                intent_scores.append({
                    'intent_space': space['name'],
                    'confidence': confidence,
                    'matches': matches,
                    'matched_keywords': matched_keywords
                })

        # Sort by matches (descending)
        intent_scores.sort(key=lambda x: x['matches'], reverse=True)

        if intent_scores and intent_scores[0]['matches'] >= 1:
            best = intent_scores[0]
            logger.info(
                f"Keyword match: {best['intent_space']} "
                f"({best['matches']} keywords: {best['matched_keywords']})"
            )
            return {
                'intent_space': best['intent_space'],
                'confidence': best['confidence'],
                'valid': True,
                'method': 'keyword'
            }

        return None

    def _get_cache_key(self, query: str, intent_spaces_json: str) -> str:
        """
        Generate cache key from query and intent spaces

        Args:
            query: User query
            intent_spaces_json: JSON string of intent spaces

        Returns:
            MD5 hash for cache key
        """
        combined = f"{query}:{intent_spaces_json}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cache entry is still valid"""
        return datetime.utcnow() - timestamp < self._cache_ttl

    def classify(
        self,
        query: str,
        intent_spaces: List[Dict]
    ) -> Dict[str, any]:
        """
        Classify query into intent space with caching

        Args:
            query: User's question
            intent_spaces: List of available intent spaces

        Returns:
            Dictionary with intent_space, confidence, and metrics
        """
        start_time = datetime.utcnow()
        self.stats['total_requests'] += 1

        # FAST PATH: Try keyword-based classification first (avoid LLM call)
        keyword_result = self._classify_by_keywords(query, intent_spaces)
        if keyword_result:
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.info(f"[KEYWORD] {keyword_result['intent_space']} (confidence: {keyword_result['confidence']:.2f}, time: {elapsed_ms}ms)")
            return {
                **keyword_result,
                'cached': False,
                'time_ms': elapsed_ms,
                'method': 'keyword'
            }

        # Try cache first
        intent_spaces_json = json.dumps(intent_spaces, sort_keys=True)
        cache_key = self._get_cache_key(query, intent_spaces_json)

        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                self.stats['cache_hits'] += 1
                elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                logger.info(f"✓ Intent cache hit: {cached_data['intent_space']} ({elapsed_ms}ms)")

                return {
                    **cached_data,
                    'cached': True,
                    'time_ms': elapsed_ms
                }
            else:
                # Remove expired cache
                del self._cache[cache_key]

        # Cache miss - use LLM
        self.stats['llm_calls'] += 1
        logger.info(f"✗ Intent cache miss, calling LLM...")

        result = self._classify_with_llm(query, intent_spaces)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update stats
        if self.stats['llm_calls'] == 1:
            self.stats['avg_llm_time_ms'] = elapsed_ms
        else:
            # Exponential moving average
            alpha = 0.2
            self.stats['avg_llm_time_ms'] = int(
                alpha * elapsed_ms + (1 - alpha) * self.stats['avg_llm_time_ms']
            )

        # Cache the result
        self._cache[cache_key] = (result, datetime.utcnow())

        logger.info(
            f"→ Intent classified: {result['intent_space']} "
            f"(confidence: {result['confidence']:.2f}, time: {elapsed_ms}ms)"
        )

        return {
            **result,
            'cached': False,
            'time_ms': elapsed_ms
        }

    def classify_simple(self, query: str) -> Dict[str, any]:
        """
        Simple classification without needing to pass intent_spaces

        This method uses cached intent_spaces from database or loads them on demand.
        It's the recommended way to classify queries in production.

        Args:
            query: User's question

        Returns:
            Dictionary with intent_space, confidence, and metrics
        """
        start_time = datetime.utcnow()
        self.stats['total_requests'] += 1

        # Get or load intent_spaces
        intent_spaces = self._get_cached_intent_spaces()

        # Try result cache first
        intent_spaces_json = json.dumps(intent_spaces, sort_keys=True)
        cache_key = self._get_cache_key(query, intent_spaces_json)

        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                self.stats['cache_hits'] += 1
                elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                logger.info(f"[HIT] {cached_data['intent_space']} ({elapsed_ms}ms)")
                return {
                    **cached_data,
                    'cached': True,
                    'time_ms': elapsed_ms
                }
            else:
                del self._cache[cache_key]

        # Cache miss - use LLM
        self.stats['llm_calls'] += 1

        result = self._classify_with_llm(query, intent_spaces)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update stats
        if self.stats['llm_calls'] == 1:
            self.stats['avg_llm_time_ms'] = elapsed_ms
        else:
            alpha = 0.2
            self.stats['avg_llm_time_ms'] = int(
                alpha * elapsed_ms + (1 - alpha) * self.stats['avg_llm_time_ms']
            )

        # Cache the result
        self._cache[cache_key] = (result, datetime.utcnow())

        logger.info(
            f"[LLM] {result['intent_space']} "
            f"({result['confidence']:.2f}, {elapsed_ms}ms)"
        )

        return {
            **result,
            'cached': False,
            'time_ms': elapsed_ms,
            'method': 'llm'
        }

    def _get_cached_intent_spaces(self) -> List[Dict]:
        """
        Get cached intent_spaces from database with TTL refresh

        This avoids querying the database on every classification call.

        Returns:
            List of intent space dictionaries
        """
        # Check if cache is valid
        if (self._intent_spaces_cache is not None and
            self._intent_spaces_cache_time and
            datetime.utcnow() - self._intent_spaces_cache_time < self._intent_spaces_cache_ttl):
            self.stats['intent_spaces_cache_hits'] += 1
            return self._intent_spaces_cache

        # Load from database
        from backend.core.database import SessionLocal
        from backend.models.database import IntentSpace

        db = SessionLocal()
        try:
            intent_spaces = db.query(IntentSpace).all()

            self._intent_spaces_cache = [
                {
                    'id': space.id,
                    'name': space.name,
                    'description': space.description,
                    'keywords': space.keywords
                }
                for space in intent_spaces
            ]
            self._intent_spaces_cache_time = datetime.utcnow()

            logger.debug(f"Refreshed intent_spaces cache ({len(self._intent_spaces_cache)} spaces)")
            return self._intent_spaces_cache
        finally:
            db.close()

    def set_intent_spaces(self, intent_spaces: List[Dict]):
        """
        Manually set intent_spaces cache (used for preloading)

        Args:
            intent_spaces: List of intent space dictionaries
        """
        self._intent_spaces_cache = intent_spaces
        self._intent_spaces_cache_time = datetime.utcnow()
        logger.info(f"Intent spaces cache set manually ({len(intent_spaces)} spaces)")

    def _classify_with_llm(
        self,
        query: str,
        intent_spaces: List[Dict]
    ) -> Dict[str, any]:
        """
        Use lightweight LLM for classification

        Args:
            query: User's question
            intent_spaces: List of available intent spaces

        Returns:
            Classification result
        """
        # Build enhanced prompt with dynamic intent spaces from database
        # Use cached descriptions to avoid rebuilding on every call
        intent_descriptions = self._get_cached_descriptions(intent_spaces)

        # Simplified system prompt for faster processing
        system_prompt = """将用户查询分类到最合适的意图空间。根据描述和关键词匹配，选择最相关的空间。General仅用于不匹配任何特定意图空间的情况。"""

        user_prompt = f"""意图空间：
{intent_descriptions}

查询：{query}

返回格式：
INTENT: [空间名称]
CONFIDENCE: [0.0-1.0]
REASON: [简短理由]"""

        try:
            response = Generation.call(
                model=self.classification_model,  # Use lightweight model
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                result_format='message',
                max_tokens=100,  # Reduced from 150
                temperature=0.1,  # Lowered from 0.2
                top_p=0.8  # Lowered from 0.9
            )

            if response.status_code == 200:
                result_text = response.output.choices[0]['message']['content']

                # Log LLM raw response for debugging
                logger.info(f"[LLM Raw Response]: {result_text}")

                # Parse response
                intent = None
                confidence = 0.0
                reason = ""

                for line in result_text.split('\n'):
                    line = line.strip()

                    if line.upper().startswith('INTENT:'):
                        intent = line.replace('INTENT:', '').replace('INTENT：', '').strip()

                    elif line.upper().startswith('CONFIDENCE:'):
                        try:
                            confidence_str = line.replace('CONFIDENCE:', '').replace('CONFIDENCE：', '').strip()
                            confidence = float(confidence_str)
                            confidence = max(0.0, min(1.0, confidence))
                        except ValueError:
                            confidence = 0.5

                    elif line.upper().startswith('REASON:'):
                        reason = line.replace('REASON:', '').replace('REASON：', '').strip()

                # Validate intent against available spaces
                valid_intents = [space['name'] for space in intent_spaces]
                if intent not in valid_intents:
                    # Try case-insensitive match
                    intent_lower = intent.lower()
                    for valid_intent in valid_intents:
                        if valid_intent.lower() == intent_lower:
                            intent = valid_intent
                            logger.info(f"Matched intent with case-insensitive lookup: {intent}")
                            break
                    else:
                        # Still not found, fallback
                        logger.warning(
                            f"Invalid intent '{intent}', expected one of {valid_intents}. "
                            f"Falling back to first valid intent."
                        )
                        intent = valid_intents[0] if valid_intents else "General"
                        confidence = 0.4

                # Boost confidence for high-confidence patterns
                confidence = self._boost_confidence(query, intent, confidence, intent_spaces)

                return {
                    'intent_space': intent,
                    'confidence': confidence,
                    'reason': reason,
                    'valid': confidence >= self.confidence_threshold
                }
            else:
                logger.error(f"Intent classification failed: {response.message}")
                return self._fallback_classification(intent_spaces)

        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return self._fallback_classification(intent_spaces)

    def _build_intent_descriptions(self, intent_spaces: List[Dict]) -> str:
        """
        Build formatted intent space descriptions for classification prompt

        This method formats intent space data from database into a clear,
        structured format that LLM can easily understand. Business users
        can modify descriptions and keywords in the database to improve
        classification accuracy without changing code.

        Args:
            intent_spaces: List of intent space dictionaries with keys:
                          - name: Intent space name (e.g., "HR", "Legal")
                          - description: Business domain description
                          - keywords: List of relevant keywords

        Returns:
            Formatted string with structure:
            INTENT_NAME: Description
            关键词: keyword1, keyword2, keyword3
        """
        descriptions = []

        for idx, space in enumerate(intent_spaces, 1):
            name = space['name']
            description = space.get('description', '无描述')

            # Parse keywords from comma-separated string or list
            keywords_raw = space.get('keywords', [])
            if isinstance(keywords_raw, str):
                keywords_list = [kw.strip() for kw in keywords_raw.split(',') if kw.strip()]
            else:
                keywords_list = keywords_raw

            keywords_str = ", ".join(keywords_list) if keywords_list else "无"

            # Format: numbered for clarity
            formatted = f"{idx}. **{name}**\n"
            formatted += f"   描述：{description}\n"
            formatted += f"   关键词：{keywords_str}"

            descriptions.append(formatted)

        return "\n\n".join(descriptions)

    def _get_intent_spaces_hash(self, intent_spaces: List[Dict]) -> str:
        """
        Generate a hash of intent spaces to detect changes

        Args:
            intent_spaces: List of intent space dictionaries

        Returns:
            MD5 hash string
        """
        intent_spaces_json = json.dumps(intent_spaces, sort_keys=True)
        return hashlib.md5(intent_spaces_json.encode()).hexdigest()

    def _get_cached_descriptions(self, intent_spaces: List[Dict]) -> str:
        """
        Get cached intent descriptions, rebuilding only if intent_spaces changed

        This significantly improves performance by avoiding expensive
        string formatting on every classification call.

        Args:
            intent_spaces: List of intent space dictionaries

        Returns:
            Formatted intent descriptions string
        """
        # Calculate hash of current intent spaces
        current_hash = self._get_intent_spaces_hash(intent_spaces)

        # Check if we have cached descriptions for this configuration
        if current_hash == self._last_intent_spaces_hash:
            self.stats['descriptions_cache_hits'] += 1
            return self._intent_descriptions_cache

        # Build new descriptions
        descriptions = self._build_intent_descriptions(intent_spaces)

        # Update cache
        self._intent_descriptions_cache = descriptions
        self._last_intent_spaces_hash = current_hash

        logger.debug(f"Rebuilt intent descriptions cache (hash: {current_hash[:8]}...)")

        return descriptions

    def _boost_confidence(
        self,
        query: str,
        intent: str,
        base_confidence: float,
        intent_spaces: List[Dict]
    ) -> float:
        """
        Boost confidence based on keyword matching from database

        This method provides a post-hoc validation of LLM classification
        by checking if the query contains keywords from the classified
        intent space. This helps catch LLM hallucinations and improves
        overall accuracy.

        Args:
            query: User query
            intent: Classified intent name
            base_confidence: Base confidence from LLM (0.0-1.0)
            intent_spaces: Available intent spaces from database

        Returns:
            Boosted confidence score (capped at 1.0)

        Boosting rules:
        - ≥3 keywords match: +0.20 (strong validation)
        - 2 keywords match: +0.10 (good validation)
        - 1 keyword match: +0.05 (weak validation)
        - 0 keywords match: no boost (LLM may be wrong, keep base confidence)
        """
        query_lower = query.lower()

        # Find intent space info from database
        intent_space_info = None
        for space in intent_spaces:
            if space['name'] == intent:
                intent_space_info = space
                break

        if not intent_space_info:
            logger.warning(f"Intent space '{intent}' not found in provided list")
            return base_confidence

        # Parse keywords from comma-separated string or list
        keywords_raw = intent_space_info.get('keywords', [])
        if isinstance(keywords_raw, str):
            keywords_list = [kw.strip().lower() for kw in keywords_raw.split(',') if kw.strip()]
        else:
            keywords_list = [kw.lower() for kw in keywords_raw]

        # Count keyword matches in query
        keyword_matches = 0
        matched_keywords = []
        for kw in keywords_list:
            if kw in query_lower:
                keyword_matches += 1
                matched_keywords.append(kw)

        # Log keyword matching for debugging
        if matched_keywords:
            logger.debug(
                f"Query matched {keyword_matches} keywords in {intent}: {matched_keywords}"
            )

        # Boost confidence based on keyword matches
        if keyword_matches >= 3:
            boosted = min(base_confidence + 0.20, 1.0)  # Strong validation
            logger.info(f"Strong keyword match ({keyword_matches}): {base_confidence:.2f} → {boosted:.2f}")
            return boosted
        elif keyword_matches >= 2:
            boosted = min(base_confidence + 0.10, 1.0)  # Good validation
            logger.info(f"Good keyword match ({keyword_matches}): {base_confidence:.2f} → {boosted:.2f}")
            return boosted
        elif keyword_matches >= 1:
            boosted = min(base_confidence + 0.05, 1.0)  # Weak validation
            logger.debug(f"Weak keyword match ({keyword_matches}): {base_confidence:.2f} → {boosted:.2f}")
            return boosted
        else:
            # No keyword match - may indicate LLM error, don't boost
            logger.warning(f"No keyword matches for {intent} (confidence: {base_confidence:.2f})")
            return base_confidence

    def _fallback_classification(self, intent_spaces: List[Dict]) -> Dict[str, any]:
        """
        Fallback classification when LLM fails

        Args:
            intent_spaces: Available intent spaces

        Returns:
            Default classification
        """
        default_intent = intent_spaces[0]['name'] if intent_spaces else "General"
        return {
            'intent_space': default_intent,
            'confidence': 0.3,
            'reason': 'LLM调用失败，使用默认分类',
            'valid': False
        }

    def clear_cache(self):
        """Clear all cached classifications"""
        self._cache.clear()
        logger.info("Intent classification cache cleared")

    def get_stats(self) -> Dict[str, any]:
        """Get classification statistics"""
        total = self.stats['total_requests']
        cache_hit_rate = (self.stats['cache_hits'] / total * 100) if total > 0 else 0
        descriptions_hit_rate = (self.stats['descriptions_cache_hits'] / total * 100) if total > 0 else 0
        intent_spaces_hit_rate = (self.stats['intent_spaces_cache_hits'] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'descriptions_cache_hit_rate': round(descriptions_hit_rate, 2),
            'intent_spaces_cache_hit_rate': round(intent_spaces_hit_rate, 2),
            'cache_size': len(self._cache)
        }


# Global instance
intent_classifier = IntentClassifier()
