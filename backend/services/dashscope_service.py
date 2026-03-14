"""DashScope integration for embeddings and LLM"""
import dashscope
from dashscope import TextEmbedding, Generation
from dashscope import MultiModalConversation
from http import HTTPStatus
from typing import List, Dict, Optional
from backend.config import settings
import logging
import re
import base64

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect if text is in Chinese or English based on character analysis

    Args:
        text: Input text to analyze

    Returns:
        'zh' for Chinese, 'en' for English
    """
    # Count Chinese characters (Unicode range for CJK Unified Ideographs)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())

    if total_chars == 0:
        return 'en'

    # If more than 30% of characters are Chinese, treat as Chinese
    chinese_ratio = chinese_chars / total_chars
    if chinese_ratio > 0.3:
        return 'zh'
    else:
        return 'en'

# Configure DashScope API
dashscope.api_key = settings.dashscope_api_key


class DashScopeService:
    """Service for DashScope AI models"""

    def __init__(self):
        self.embedding_model = settings.embedding_model
        self.vision_model = settings.vision_model
        self.intent_model = settings.intent_model
        self.llm_model = settings.llm_model
        self.temperature = settings.temperature
        self.max_tokens = min(max(settings.max_tokens, 1), 8192)  # Ensure valid range
        self.embedding_dimension = settings.embedding_dimension
        logger.info(f"DashScopeService initialized: max_tokens={self.max_tokens}, llm_model={self.llm_model}, intent_model={self.intent_model}, vision_model={self.vision_model}")

    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text using DashScope

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding vector
        """
        try:
            resp = TextEmbedding.call(
                model=self.embedding_model,
                input=text
            )
            
            if resp.status_code == 200:
                return resp.output['embeddings'][0]['embedding']
            else:
                logger.error(f"Embedding generation failed: {resp.message}")
                raise Exception(f"Embedding error: {resp.message}")
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            try:
                embedding = self.get_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error embedding text: {e}")
                # Return zero vector on error
                embeddings.append([0.0] * self.embedding_dimension)
        return embeddings

    def extract_table_from_image(self, image_data: bytes, page_context: str = "") -> Optional[Dict]:
        """
        Use multi-modal vision model to extract structured table from image

        Args:
            image_data: Image bytes data (from PDF page rendering)
            page_context: Optional text context from the page for better understanding

        Returns:
            Dictionary with extracted table data or None if no table found
        """
        try:
            # Convert image to base64 for API call
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Build prompt for table extraction
            prompt = """Please analyze this image and extract any tables present.

Requirements:
1. Identify if the image contains a table
2. If yes, extract:
   - Table title (if any)
   - Column headers
   - All data rows
   - Preserve numerical values exactly

Output format (if table found):
[TABLE]
Title: [table title]
Headers: [col1, col2, col3, ...]
Row 1: [val1, val2, val3, ...]
Row 2: [val1, val2, val3, ...]
[END TABLE]

If no table is found, output:
[NO TABLE]"""

            # Add context if provided
            if page_context:
                prompt += f"\n\nContext text from this page:\n{page_context[:500]}"

            # Build multimodal message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": base64_image
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]

            # Call multimodal API
            response = MultiModalConversation.call(
                model=self.vision_model,
                messages=messages
            )

            if response.status_code == HTTPStatus.OK:
                result_text = response.output.choices[0]['message']['content'][0]['text']
                logger.info(f"Vision model response length: {len(result_text)}")

                # Parse the result
                if "[NO TABLE]" in result_text:
                    logger.info("No table detected by vision model")
                    return None

                if "[TABLE]" in result_text:
                    # Extract table content
                    table_data = self._parse_table_response(result_text)
                    return {
                        'type': 'table',
                        'extracted': True,
                        'method': 'vision',
                        'data': table_data,
                        'raw_response': result_text
                    }

                # Fallback: return raw response if format doesn't match
                logger.warning(f"Unexpected response format: {result_text[:200]}")
                return {
                    'type': 'table',
                    'extracted': True,
                    'method': 'vision',
                    'data': {'title': '', 'headers': [], 'rows': []},
                    'raw_response': result_text
                }
            else:
                logger.error(f"Vision API call failed: {response.code} - {response.message}")
                return None

        except Exception as e:
            logger.error(f"Error extracting table from image: {e}")
            return None

    def _parse_table_response(self, response_text: str) -> Dict:
        """
        Parse the structured table response from vision model

        Args:
            response_text: Raw response text from vision model

        Returns:
            Dictionary with title, headers, and rows
        """
        table_data = {
            'title': '',
            'headers': [],
            'rows': []
        }

        lines = response_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith('Title:'):
                table_data['title'] = line.replace('Title:', '').strip()
            elif line.startswith('Headers:'):
                headers_str = line.replace('Headers:', '').strip()
                # Parse headers: [col1, col2, ...] or col1, col2, ...
                if headers_str.startswith('[') and headers_str.endswith(']'):
                    headers_str = headers_str[1:-1]
                table_data['headers'] = [h.strip() for h in headers_str.split(',')]
            elif line.startswith('Row'):
                row_str = line.replace('Row', '').strip()
                # Remove leading number and colon: "1:" or "2:"
                if ':' in row_str:
                    row_str = row_str.split(':', 1)[1].strip()
                if row_str.startswith('[') and row_str.endswith(']'):
                    row_str = row_str[1:-1]
                table_data['rows'].append([v.strip() for v in row_str.split(',')])
            elif line == '[END TABLE]':
                break

        return table_data

    def generate_response(
        self,
        query: str,
        context: str,
        intent_space: str = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate response using LLM with context from knowledge base

        Args:
            query: User's question
            context: Retrieved context from knowledge base
            intent_space: Current intent space for context
            max_tokens: Maximum tokens for response (optional)

        Returns:
            Generated response text
        """
        max_tokens = max_tokens or self.max_tokens

        # Ensure max_tokens is within valid range [1, 8192]
        max_tokens = min(max(1, max_tokens), 8192)

        # Detect language
        lang = detect_language(query)
        logger.info(f"Detected language: {lang}")

        logger.info(f"Generating response with max_tokens={max_tokens}")

        # Build prompt with context (language-specific) - 强调简洁和引用
        if lang == 'zh':
            system_prompt = f"""你是一个{intent_space or '通用'}知识管理系统的助手。任务：基于知识库上下文简洁回答。

核心规则：
1. **简洁为主**：控制在200字以内（如需列表可适当扩展）
2. **必须引用**：每个关键信息后标注来源，格式为「来源：文档名」，例如：（来源：年假政策）
3. **使用项目符号**：多用简洁的要点列表
4. **优先回答**：上下文中如有相关信息，必须基于此回答。只有当上下文确实没有相关信息时，才说明"知识库中暂无相关信息"
5. **格式统一**：使用 • 或 1. 2. 3. 编号

引用示例：
• 员工享有15天年假（来源：年假政策）
• 需提前1个月申请（来源：请假流程）"""
            user_prompt = f"""上下文信息：
{context}

问题：{query}

要求：仔细阅读上下文，基于上下文信息回答。如上下文中有相关信息，必须基于此回答，不要说"没有相关信息"。每点后标注「来源：文档名」。"""
        else:
            system_prompt = f"""You are a {intent_space or 'general'} knowledge assistant. Task: Concise answers from KB.

Core rules:
1. **Be concise**: Keep under 150 words (lists can be slightly longer)
2. **Cite sources**: Mark key info with format (Source: DocumentName), e.g., (Source: Annual Leave Policy)
3. **Use bullets**: Prefer bullet points for clarity
4. **Prioritize context**: If context contains relevant information, ALWAYS answer based on it. Only say "No relevant information" if context truly has NO relevant information.
5. **Consistent format**: Use • or 1. 2. 3. for numbering

Citation example:
• Employees get 15 days annual leave (Source: Annual Leave Policy)
• Must apply 1 month in advance (Source: Leave Process)"""
            user_prompt = f"""Context information:
{context}

Question: {query}

Requirements: Carefully read the context. Answer based on the context if it contains relevant information. NEVER say "No relevant information" if the context provides an answer. Cite sources with format (Source: DocumentName) after each point."""

        try:
            response = Generation.call(
                model=self.llm_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                result_format='message',
                max_tokens=max_tokens,
                temperature=self.temperature
            )

            if response.status_code == 200:
                return response.output.choices[0]['message']['content']
            else:
                logger.error(f"LLM generation failed: {response.message}")
                return "I apologize, but I encountered an error generating a response. Please try again."

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "I apologize, but I encountered an error. Please try again later."

    def generate_response_stream(
        self,
        query: str,
        context: str,
        intent_space: str = None,
        max_tokens: int = None,
        stream_callback=None
    ) -> str:
        """
        Generate response using LLM with streaming support

        Args:
            query: User's question
            context: Retrieved context from knowledge base
            intent_space: Current intent space for context
            max_tokens: Maximum tokens for response (optional)
            stream_callback: Callback function called with each chunk

        Returns:
            Complete generated response text
        """
        max_tokens = max_tokens or self.max_tokens
        # 限制响应长度以保持简洁性
        max_tokens = min(max(1, max_tokens), 512)  # 从8192降至512确保简洁

        # Detect language
        lang = detect_language(query)
        logger.info(f"Detected language: {lang}")

        logger.info(f"Generating streaming response with max_tokens={max_tokens}")

        # Build prompt (language-specific)
        if lang == 'zh':
            system_prompt = f"""你是一个{intent_space or '通用'}知识管理系统的有用助手。
Your task is to answer questions based on the provided context from the knowledge base.

Rules:
1. Use only the information from the provided context
2. If the context doesn't contain relevant information, state that you don't have enough information
3. Be concise and to the point
4. Cite the source document when possible
5. Format the answer clearly with bullet points or numbered lists when appropriate"""

        user_prompt = f"""Context:
::{context}

Question: {query}

Please provide a clear and helpful answer based on the context above."""

        try:
            responses = Generation.call(
                model=self.llm_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                result_format='message',
                max_tokens=max_tokens,
                temperature=self.temperature,
                incremental_output=True
            )

            full_response = ""
            # DashScope returns an iterator when incremental_output=True
            for response in responses:
                # Check if response has status_code (it's a DashScopeResponse object)
                if hasattr(response, 'status_code'):
                    if response.status_code == 200:
                        if hasattr(response, 'output') and response.output:
                            choices = response.output.get('choices', [])
                            if choices and len(choices) > 0:
                                message = choices[0].get('message', {})
                                chunk = message.get('content', '')
                                if chunk:
                                    full_response += chunk
                                    if stream_callback:
                                        stream_callback(chunk)
                    else:
                        logger.error(f"LLM streaming error: {response.message if hasattr(response, 'message') else 'Unknown error'}")
                        break
                else:
                    # Last iteration may return the complete response as a dict
                    if isinstance(response, dict) and 'output' in response:
                        output = response['output']
                        if 'choices' in output and output['choices']:
                            chunk = output['choices'][0]['message']['content']
                            if chunk:
                                full_response += chunk
                                if stream_callback:
                                    stream_callback(chunk)
                    break

            return full_response

        except Exception as e:
            logger.error(f"Error in streaming LLM response: {e}")
            return "I apologize, but I encountered an error. Please try again later."

    def classify_intent(
        self,
        query: str,
        intent_spaces: List[Dict]
    ) -> Dict[str, any]:
        """
        Classify query into an intent space using LLM

        Args:
            query: User's question
            intent_spaces: List of available intent spaces with keywords

        Returns:
            Dictionary with intent_space, confidence, and classification details
        """
        # Build intent space descriptions
        intent_descriptions = "\n".join([
            f"- {space['name']}: {space['description']} (Keywords: {space['keywords']})"
            for space in intent_spaces
        ])

        system_prompt = """You are an expert intent classifier for a knowledge management system.
Your task is to accurately classify user queries into the most appropriate intent space.

CLASSIFICATION RULES (follow in order):

1. **LEGAL** - Classify as 'Legal' if query contains:
   - Legal terms: GDPR, compliance, contract, law, regulation, liability, terms, agreement, NDA, privacy, data protection, legal, lawsuit, litigation
   - Privacy/security terms: data breach, security policy, confidentiality, intellectual property, trademark, copyright, patent

2. **HR** - Classify as 'HR' if query contains:
   - HR terms: HR, employee, leave, benefit, salary, payroll, recruitment, onboarding, training, performance, compensation, insurance, health, retirement
   - Employment terms: hiring, firing, termination, promotion, raise, bonus, vacation, sick leave, maternity leave, paternity leave, workplace, culture, manager, supervisor, team, organization structure

3. **FINANCE** - Classify as 'Finance' if query contains:
   - Finance terms: finance, accounting, budget, expense, invoice, payment, reimbursement, tax, audit, financial, procurement, purchasing, cost, revenue, profit, loss, forecast
   - Money terms: money, cash, funding, investment, capital, asset, liability, equity, credit, debit, billing, quote, price, purchase order

4. **GENERAL** - Classify as 'General' only if:
   - Query is about company information, announcements, FAQ, help
   - Query is ambiguous and doesn't clearly fit above categories
   - Query is about general policies not covered by Legal, HR, or Finance

IMPORTANT:
- Always match EXACTLY one of the provided intent space names
- Be confident in your classification - if unsure, choose the most relevant category
- Do not default to General unless truly necessary"""

        user_prompt = f"""Available Intent Spaces:
{intent_descriptions}

Query: {query}

Analyze this query carefully and classify it into the EXACT intent space name that best matches.

Format your response as:
INTENT: [intent space name]
CONFIDENCE: [confidence score]"""

        try:
            response = Generation.call(
                model=self.intent_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                result_format='message',
                max_tokens=100,
                temperature=0.3  # Lower temperature for more consistent classification
            )

            if response.status_code == 200:
                result_text = response.output.choices[0]['message']['content']

                # Parse response
                intent = None
                confidence = 0.0

                for line in result_text.split('\n'):
                    line = line.strip().upper()
                    if line.startswith('INTENT:'):
                        intent = line.replace('INTENT:', '').strip()
                    elif line.startswith('CONFIDENCE:'):
                        try:
                            confidence = float(line.replace('CONFIDENCE:', '').strip())
                        except:
                            pass

                # Validate intent
                valid_intents = [space['name'] for space in intent_spaces]
                if intent not in valid_intents:
                    intent = "General"
                    confidence = 0.3

                return {
                    'intent_space': intent,
                    'confidence': min(confidence, 1.0),
                    'raw_response': result_text
                }
            else:
                logger.error(f"Intent classification failed: {response.message}")
                return {
                    'intent_space': 'General',
                    'confidence': 0.3,
                    'error': str(response.message)
                }

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return {
                'intent_space': 'General',
                'confidence': 0.3,
                'error': str(e)
            }


# Global instance
dashscope_service = DashScopeService()
