"""
Application configuration
"""
import os
from pathlib import Path
from typing import Optional

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_DB_DIR = BASE_DIR / "faiss_index"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/intelliknow.db")

# DashScope API (Alibaba Cloud)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# DashScope Embedding Model
DASHSCOPE_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

# DashScope Vision Model (for table extraction)
DASHSCOPE_VISION_MODEL = os.getenv("VISION_MODEL", "qwen-vl-plus")

# DashScope LLM Models
# Intent Classification Model: Lightweight, fast
DASHSCOPE_INTENT_MODEL = os.getenv("INTENT_MODEL", "qwen-turbo")
# Response Generation Model: High quality
DASHSCOPE_LLM_MODEL = os.getenv("LLM_MODEL", "qwen-turbo")

# LLM Generation Parameters
DASHSCOPE_MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
DASHSCOPE_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Document Retrieval Configuration
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "1"))

# File Upload
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

# FastAPI
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_PREFIX = "/api"
CORS_ORIGINS = ["*"]

# App metadata
APP_NAME = os.getenv("APP_NAME", "IntelliKnow KMS")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")

# Microsoft Teams Bot
TEAMS_APP_ID = os.getenv("TEAMS_APP_ID", "")
TEAMS_APP_PASSWORD = os.getenv("TEAMS_APP_PASSWORD", "")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")

# DingTalk Bot
DINGTALK_WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK_URL", "")
DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")

# Lark/Feishu Bot
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
FEISHU_ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

# LangChain Integration
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "false").lower() == "true"


class Settings:
    """Application settings"""

    def __init__(self):
        self.database_url = DATABASE_URL
        self.vector_db_dir = VECTOR_DB_DIR
        self.upload_dir = UPLOAD_DIR

        # App metadata
        self.app_name = APP_NAME
        self.app_version = APP_VERSION
        self.debug = DEBUG

        # DashScope
        self.dashscope_api_key = DASHSCOPE_API_KEY
        self.embedding_model = DASHSCOPE_EMBEDDING_MODEL
        self.vision_model = DASHSCOPE_VISION_MODEL
        self.intent_model = DASHSCOPE_INTENT_MODEL
        self.llm_model = DASHSCOPE_LLM_MODEL
        self.max_tokens = DASHSCOPE_MAX_TOKENS
        self.temperature = DASHSCOPE_TEMPERATURE
        self.embedding_dimension = EMBEDDING_DIMENSION
        self.retrieval_top_k = RETRIEVAL_TOP_K

        # File Upload
        self.max_file_size = MAX_FILE_SIZE
        self.allowed_extensions = ALLOWED_EXTENSIONS

        # FastAPI
        self.api_host = API_HOST
        self.api_port = API_PORT
        self.api_prefix = API_PREFIX
        self.cors_origins = CORS_ORIGINS

        # Telegram
        self.telegram_bot_token = TELEGRAM_BOT_TOKEN
        self.telegram_webhook_url = TELEGRAM_WEBHOOK_URL

        # Teams
        self.teams_app_id = TEAMS_APP_ID
        self.teams_app_password = TEAMS_APP_PASSWORD
        self.teams_webhook_url = TEAMS_WEBHOOK_URL

        # DingTalk
        self.dingtalk_webhook_url = DINGTALK_WEBHOOK_URL
        self.dingtalk_app_key = DINGTALK_APP_KEY
        self.dingtalk_app_secret = DINGTALK_APP_SECRET

        # Lark/Feishu
        self.feishu_app_id = FEISHU_APP_ID
        self.feishu_app_secret = FEISHU_APP_SECRET
        self.feishu_verification_token = FEISHU_VERIFICATION_TOKEN
        self.feishu_encrypt_key = FEISHU_ENCRYPT_KEY
        self.feishu_webhook_url = FEISHU_WEBHOOK_URL

        # LangChain
        self.use_langchain = USE_LANGCHAIN


settings = Settings()
