from pydantic_settings import BaseSettings

from .config import (
    APIConfig,
    AzureChatOpenAIConfig,
    AzureDocumentIntelligenceConfig,
    CeleryConfig,
    ChunkConfig,
    ConversationChatConfig,
    EmbeddingModelConfig,
    JWTConfig,
    LoggingConfig,
    MiddlewareConfig,
    MilvusConfig,
    OpenAIEmbeddingConfig,
    PostgresConfig,
    ProcessFileConfig,
    QdrantConfig,
    RedisConfig,
    S3Config,
    TavilySearchConfig,
    VLMConfig,
    ProcessingConfig,
)


class Settings(BaseSettings):
    qdrant: QdrantConfig = QdrantConfig()
    milvus: MilvusConfig = MilvusConfig()
    embedding_model: EmbeddingModelConfig = EmbeddingModelConfig()
    openai_embedding: OpenAIEmbeddingConfig = OpenAIEmbeddingConfig()
    postgres: PostgresConfig = PostgresConfig()
    s3: S3Config = S3Config()
    azure_document_intelligence: AzureDocumentIntelligenceConfig = (
        AzureDocumentIntelligenceConfig()
    )
    redis: RedisConfig = RedisConfig()
    celery: CeleryConfig = CeleryConfig()
    azure_chat_openai: AzureChatOpenAIConfig = AzureChatOpenAIConfig()
    tavily_search: TavilySearchConfig = TavilySearchConfig()
    logging: LoggingConfig = LoggingConfig()
    middleware: MiddlewareConfig = MiddlewareConfig()
    api: APIConfig = APIConfig()
    chunk: ChunkConfig = ChunkConfig()
    process_file: ProcessFileConfig = ProcessFileConfig()
    conversation_chat: ConversationChatConfig = ConversationChatConfig()
    jwt: JWTConfig = JWTConfig()
    vlm: VLMConfig = VLMConfig()
    processing: ProcessingConfig = ProcessingConfig()

    def __str__(self) -> str:
        return f"""
        Qdrant: {self.qdrant}
        Milvus: {self.milvus}
        OpenAI Embedding: {self.openai_embedding}
        Postgres: {self.postgres}
        S3: {self.s3}
        Azure Document Intelligence: {self.azure_document_intelligence}
        Redis: {self.redis}
        Celery: {self.celery}
        Azure Chat OpenAI: {self.azure_chat_openai}
        Tavily Search: {self.tavily_search}
        Logging: {self.logging}
        API: {self.api}
        Web: {self.web}
        """


_settings = Settings()
