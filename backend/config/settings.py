from pydantic_settings import BaseSettings

from .config import (
    APIConfig,
    AzureBlobStorageConfig,
    AzureChatOpenAIConfig,
    AzureDocumentIntelligenceConfig,
    AzureImageGenerationConfig,
    CeleryConfig,
    ChunkConfig,
    ConversationChatConfig,
    DataRetentionConfig,
    EmbeddingModelConfig,
    IngestionSummaryConfig,
    JWTConfig,
    LoggingConfig,
    Mem0Config,
    MiddlewareConfig,
    MilvusConfig,
    OpenAIEmbeddingConfig,
    PostgresConfig,
    ProcessFileConfig,
    QdrantConfig,
    RAGConfig,
    RedisConfig,
    S3Config,
    SkillsConfig,
    TavilySearchConfig,
    VideoGenerationConfig,
    VLMConfig,
    ProcessingConfig,
    GGSearch,
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
    azure_image_generation: AzureImageGenerationConfig = AzureImageGenerationConfig()
    tavily_search: TavilySearchConfig = TavilySearchConfig()
    gg_search: GGSearch = GGSearch()
    rag: RAGConfig = RAGConfig()
    logging: LoggingConfig = LoggingConfig()
    middleware: MiddlewareConfig = MiddlewareConfig()
    data_retention: DataRetentionConfig = DataRetentionConfig()
    api: APIConfig = APIConfig()
    chunk: ChunkConfig = ChunkConfig()
    process_file: ProcessFileConfig = ProcessFileConfig()
    conversation_chat: ConversationChatConfig = ConversationChatConfig()
    jwt: JWTConfig = JWTConfig()
    vlm: VLMConfig = VLMConfig()
    processing: ProcessingConfig = ProcessingConfig()
    ingestion_summary: IngestionSummaryConfig = IngestionSummaryConfig()
    mem0: Mem0Config = Mem0Config()
    skills: SkillsConfig = SkillsConfig()
    video_generation: VideoGenerationConfig = VideoGenerationConfig()
    azure_blob: AzureBlobStorageConfig = AzureBlobStorageConfig()

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
