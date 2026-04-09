from ctypes import Union
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()


def _env(*keys: str, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def _env_bool(*keys: str, default: bool = False) -> bool:
    value = _env(*keys, default=None)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(*keys: str, default: int) -> int:
    value = _env(*keys, default=None)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_csv(*keys: str, default: str = "") -> List[str]:
    raw = _env(*keys, default=default) or ""
    return [item.strip() for item in str(raw).split(",") if item.strip()]


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

    api_key: str = _env(
        "AZURE-OPENAI-GPT51-API-KEY",
        "AZURE_OPENAI_GPT51_API_KEY",
        "AZURE_OPENAI_KEY",
    )
    api_endpoint: str = _env(
        "AZURE-OPENAI-GPT51-ENDPOINT",
        "AZURE_OPENAI_GPT51_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT",
    )
    api_version: str = _env(
        "AZURE-OPENAI-GPT51-API-VERSION",
        "AZURE_OPENAI_GPT51_API_VERSION",
        "AZURE_OPENAI_API_VERSION",
        default="2025-04-01-preview",
    )
    deployment_name_gpt_5_1: str = _env(
        "AZURE-OPENAI-GPT51-DEPLOYMENT-NAME",
        "AZURE_OPENAI_GPT51_DEPLOYMENT_NAME",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        default="gpt-5.1",
    )
    deployment_name_gpt_4_1: str = _env(
        "AZURE_OPENAI_GPT41_DEPLOYMENT_NAME",
        default="gpt-4.1",
    )
    deployment_name_gpt_4_1_mini: str = _env(
        "AZURE_OPENAI_GPT41_MINI_DEPLOYMENT_NAME",
        default="gpt-4.1-mini",
    )
    temperature: float = 0.0


@dataclass
class AzureImageGenerationConfig:
    """Azure Image Generation configuration settings."""

    api_key: str = _env(
        "AZURE-OPENAI-IMAGE-API-KEY",
        "AZURE_OPENAI_IMAGE_KEY",
        "AZURE_OPENAI_KEY",
        default="",
    )
    api_endpoint: str = _env(
        "AZURE-OPENAI-IMAGE-ENDPOINT",
        "AZURE_OPENAI_IMAGE_ENDPOINT",
        default="",
    )
    api_version: str = _env(
        "AZURE-OPENAI-IMAGE-API-VERSION",
        default="2024-02-15-preview",
    )
    deployment_name: str = _env(
        "AZURE_OPENAI_IMAGE_DEPLOYMENT",
        default="gpt-image-1",
    )
    default_size: str = "1024x1024"
    default_quality: str = "standard"
    default_n: int = 1


@dataclass
class RAGConfig:
    """RAG configuration settings."""

    hybrid_alpha: float = 0.7
    vector_top_k: int = 10
    bm25_top_k: int = 10
    rerank_top_n: int = 5
    max_context_tokens: int = 4000


@dataclass
class EmbeddingModelConfig:
    """Embedding model configuration settings."""

    dense_model: str = "text-embedding-3-large"
    dense_embedding_size: int = 3072
    sparse_model: str = "Qdrant/bm25"


@dataclass
class OpenAIEmbeddingConfig:
    """OpenAI embedding configuration."""

    api_key: str = _env(
        "AZURE-OPENAI-EMBEDDING-KEY",
        "AZURE_OPENAI_EMBEDDING_KEY",
        "OPENAI_API_KEY",
    )
    endpoint: str = _env(
        "AZURE-OPENAI-EMBEDDING-ENDPOINT",
        "AZURE_OPENAI_EMBEDDING_ENDPOINT",
    )
    api_version: str = _env(
        "AZURE-OPENAI-EMBEDDING-API-VERSION",
        "AZURE_OPENAI_EMBEDDING_API_VERSION",
        default="2023-05-15",
    )
    api_base: str = _env("OPENAI_API_BASE", default="https://api.openai.com/v1")
    embedding_model: str = _env(
        "AZURE-OPENAI-EMBEDDING-DEPLOYMENT-NAME",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME",
        "OPENAI_EMBEDDING_MODEL",
        default="text-embedding-3-large",
    )
    embedding_dimension: int = int(_env("OPENAI_EMBEDDING_DIMENSION", default="3072"))
    batch_size: int = int(_env("OPENAI_EMBEDDING_BATCH_SIZE", default="32"))
    timeout_seconds: int = int(_env("OPENAI_EMBEDDING_TIMEOUT_SECONDS", default="120"))


@dataclass
class MilvusConfig:
    """Milvus configuration settings."""

    host: str = os.getenv("MILVUS_HOST", "localhost")
    port: str = os.getenv("MILVUS_PORT", "19530")
    user: str = os.getenv("MILVUS_USER", "")
    password: str = os.getenv("MILVUS_PASSWORD", "")
    collection_name: str = os.getenv("MILVUS_COLLECTION_NAME", "document_chunks")
    metric_type: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    index_type: str = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
    nlist: int = int(os.getenv("MILVUS_INDEX_NLIST", "1024"))
    consistency_level: str = os.getenv("MILVUS_CONSISTENCY_LEVEL", "Strong")


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file: str = os.getenv("LOG_FILE", "logs/backend.log")
    log_format: str = os.getenv(
        "LOG_FORMAT",
        (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | service={extra[service]} "
            "request_id={extra[request_id]} "
            "user_id={extra[user_id]} | {name}:{function}:{line} | "
            "{message}"
        ),
    )


@dataclass
class TavilySearchConfig:
    """Tavily Search configuration settings."""

    api_key: str = _env("TAVILY-SEARCH-API-KEY", "TAVILY_SEARCH_API_KEY")
    api_endpoint: str = _env("TAVILY-SEARCH-API-ENDPOINT", "TAVILY_SEARCH_API_ENDPOINT")
    include_answer: bool = False
    search_depth: str = "advanced"
    exclude_domains: List[str] = field(default_factory=list)

from typing import Optional

class GGSearch:
    gg_search_url: Optional[str]
    gg_search_engine_id: Optional[str]
    current_key_index: int

    def __init__(self) -> None:
        self.gg_search_url = os.getenv("GOOGLE-SEARCH-URL", "")
        self.gg_search_engine_id = os.getenv("GOOGLE-SEARCHENGINE-ID", "")

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
class MiddlewareConfig:
    """HTTP middleware configuration settings."""

    request_logging_enabled: bool = _env_bool(
        "MIDDLEWARE_REQUEST_LOGGING_ENABLED",
        default=True,
    )
    rate_limit_enabled: bool = _env_bool(
        "MIDDLEWARE_RATE_LIMIT_ENABLED",
        default=True,
    )
    rate_limit_requests: int = _env_int(
        "MIDDLEWARE_RATE_LIMIT_REQUESTS",
        default=120,
    )
    rate_limit_window_seconds: int = _env_int(
        "MIDDLEWARE_RATE_LIMIT_WINDOW_SECONDS",
        default=60,
    )
    rate_limit_excluded_paths: List[str] = field(
        default_factory=lambda: _env_csv(
            "MIDDLEWARE_RATE_LIMIT_EXCLUDED_PATHS",
            default="/docs,/redoc,/openapi.json,/socket.io,/healthz",
        )
    )
    rate_limit_trust_x_forwarded_for: bool = _env_bool(
        "MIDDLEWARE_RATE_LIMIT_TRUST_X_FORWARDED_FOR",
        default=True,
    )
    security_headers_enabled: bool = _env_bool(
        "MIDDLEWARE_SECURITY_HEADERS_ENABLED",
        default=True,
    )


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

@dataclass
class VLMConfig:
    """Configuration for Vision-Language Model (VLM) services."""

    default_seed: int = 42
    default_timeout: int = 120
    default_max_completion_tokens: int = 512
    default_prompt: str = "Describe the image in three sentences. Be concise and accurate."
    default_host: str = "localhost"
    vllm_default_port: int = 8000
    lms_default_port: int = 1234

@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    default_num_threads: int = 4
    default_ocr_batch_size: int = 4
    default_layout_batch_size: int = 64
    default_table_batch_size: int = 4

    default_ocr_languages: list = None

    def __post_init__(self):
        """Initialize default values that can't be set as class variables."""
        if self.default_ocr_languages is None:
            self.default_ocr_languages = ["auto"]


@dataclass
class Mem0Config:
    """Mem0 long-term memory configuration."""
    
    # Vector store (Milvus - reuse existing infrastructure)
    vector_store_provider: str = os.getenv("MEM0_VECTOR_STORE_PROVIDER", "milvus")
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: str = os.getenv("MILVUS_PORT", "19530")
    memory_collection_name: str = os.getenv("MEM0_MILVUS_COLLECTION", "user_memories")
    
    # Embedding dimensions (match existing Milvus config)
    embedding_dims: int = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", "3072"))
    
    # History storage
    history_db_path: str = os.getenv(
        "MEM0_HISTORY_DB_PATH",
        os.path.expanduser("~/.mem0/history.db")
    )
    
    # Memory retrieval settings
    memory_top_k: int = int(os.getenv("MEM0_MEMORY_TOP_K", "10"))
    memory_score_threshold: float = float(os.getenv("MEM0_MEMORY_SCORE_THRESHOLD", "0.5"))
    
    # Feature toggle
    enable_long_term_memory: bool = _env_bool(
        "MEM0_ENABLE_LONG_TERM_MEMORY",
        default=True
    )
