import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()


@dataclass
class QdrantConfig:
    """Database configuration settings."""

    qdrant_host: str = os.getenv("QDRANT_HOST")
    qdrant_port: str = os.getenv("QDRANT_PORT")
    qdrant_url: str = f"http://{qdrant_host}:{qdrant_port}"
    qdrant_timeout: int = 3600
    qdrant_batch_size: int = 100

    # collection names
    default_collection: str = "default_collection"
    company_collection: str = "company_collection"
    project_collection: str = "project_collection"
    experience_collection: str = "experience_collection"
    limit: int = 3


@dataclass
class PostgresConfig:
    """Postgres configuration settings."""

    driver: str = "postgresql+psycopg2"
    host: str = os.getenv("POSTGRES_HOST")
    port: str = os.getenv("POSTGRES_PORT")
    user: str = os.getenv("POSTGRES_USER")
    password: str = os.getenv("POSTGRES_PASSWORD")
    database: str = os.getenv("POSTGRES_DB")
    url: str = f"{driver}://{user}:{password}@{host}:{port}/{database}"
    pool_size = 50
    max_overflow = 50
    pool_timeout = 30
    pool_recycle = 1800


@dataclass
class JWTConfig:
    """JWT configuration settings."""

    secret_key: str = os.getenv("JWT_SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 5 * 60  # 5 hours
    refresh_token_expire_minutes: int = 60 * 24 * 30 * 2  # 60 days


@dataclass
class S3Config:
    """S3 configuration settings."""

    access_key_id: str = os.getenv("S3_ACCESS_KEY_ID")
    secret_access_key: str = os.getenv("S3_SECRET_ACCESS_KEY")
    region: str = os.getenv("S3_REGION")
    endpoint: str = os.getenv("S3_ENDPOINT")
    bucket_name: str = os.getenv("S3_BUCKET_NAME")
    prefix: str = "ugate-ai/images"


@dataclass
class AzureDocumentIntelligenceConfig:
    """Document processing configuration settings."""

    api_key: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    api_endpoint: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    max_concurrent_requests: int = 3
    processed_image_dir: str = "tmp"
    azure_api_timeout: int = 3600
    azure_retry_attempts: int = 3


@dataclass
class RedisConfig:
    """Redis configuration settings."""

    url: str = os.getenv("REDIS_URL")


@dataclass
class CeleryConfig:
    """Celery configuration settings."""

    broker_url: str = os.getenv("REDIS_URL")
    result_backend: str = os.getenv("REDIS_URL")
    app_name: str = "files"
    timezone: str = "UTC"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = field(default_factory=lambda: ["json"])
    include: List[str] = field(default_factory=lambda: ["core.files.tasks"])
    enable_utc: bool = True
    task_routes: Dict[str, str] = field(
        default_factory=lambda: {"process_file": "pipeline_processing"}
    )
    worker_prefetch_multiplier: int = 1
    task_acks_late: bool = True
    worker_disable_rate_limits: bool = False
    task_always_eager: bool = False
    task_eager_propagates: bool = True
    task_max_retries: int = 0
    task_time_limit: int = 3600
    task_soft_time_limit: int = 3300
    result_expires: int = 3600
    result_persistent: bool = True


@dataclass
class AzureChatOpenAIConfig:
    """Azure Chat OpenAI configuration settings."""

    api_key: str = os.getenv("AZURE_OPENAI_KEY")
    api_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version: str = "2025-01-01-preview"
    deployment_name_gpt_4_1: str = "gpt-4.1"
    deployment_name_gpt_4_1_mini: str = "gpt-4.1-mini"
    temperature: float = 0.0


@dataclass
class EmbeddingModelConfig:
    """Embedding model configuration settings."""

    dense_model: str = "text-embedding-3-large"
    dense_embedding_size: int = 3072
    sparse_model: str = "Qdrant/bm25"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    log_level: str = "INFO"
    log_file: str = "logs/langgraph.log"
    log_format: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )


@dataclass
class TavilySearchConfig:
    """Tavily Search configuration settings."""

    api_key: str = os.getenv("TAVILY_SEARCH_API_KEY")
    api_endpoint: str = os.getenv("TAVILY_SEARCH_API_ENDPOINT")
    max_results: int = 10
    include_answer: bool = False
    search_depth: str = "advanced"
    allowed_domains: List[str] = field(
        default_factory=lambda: [
            "https://www.siemens.com",
            "https://www.mitsubishi-electric.vn",
            "https://www.se.com/",
            "https://udata.ai/",
        ]
    )
    exclude_domains: List[str] = field(default_factory=list)


@dataclass
class WebConfig:
    be_base_url: str = "https://be.ugate.vn"
    authen_token: str = os.getenv("BE_CALLBACK_TOKEN")
    fe_url: str = "https://ugate.vn"


@dataclass
class APIConfig:
    """API configuration settings."""

    # CORS origins
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:8000"])

    # API settings
    title: str = "Ugate Agent"
    version: str = "1.0"
    docs_enabled: bool = True


@dataclass
class ChunkConfig:
    """Chunk configuration settings."""

    chunk_size: int = 1000
    chunk_overlap: int = 100
    markdown_headers: List[Tuple[str, str]] = field(
        default_factory=lambda: [
            ("#", "header1"),
            ("##", "header2"),
            ("###", "header3"),
        ]
    )
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


@dataclass
class ProcessFileConfig:
    """Process file configuration settings."""

    root_download_folder: str = "tmp"
    download_timeout: int = 3600
    max_retries: int = 3
    retry_delay: int = 60


@dataclass
class ConversationChatConfig:
    """Conversation chat configuration settings."""

    nums_history_messages: int = 30
