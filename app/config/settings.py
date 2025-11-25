from .config import *
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    qdrant: QdrantConfig = QdrantConfig()
    embedding_model: EmbeddingModelConfig = EmbeddingModelConfig()
    postgres: PostgresConfig = PostgresConfig()
    s3: S3Config = S3Config()
    azure_document_intelligence: AzureDocumentIntelligenceConfig = AzureDocumentIntelligenceConfig()
    redis: RedisConfig = RedisConfig()
    celery: CeleryConfig = CeleryConfig()
    azure_chat_openai: AzureChatOpenAIConfig = AzureChatOpenAIConfig()
    tavily_search: TavilySearchConfig = TavilySearchConfig()
    logging: LoggingConfig = LoggingConfig()
    api: APIConfig = APIConfig()
    web: WebConfig = WebConfig()
    chunk: ChunkConfig = ChunkConfig()
    process_file: ProcessFileConfig = ProcessFileConfig()
    conversation_chat: ConversationChatConfig = ConversationChatConfig()
    def __str__(self) -> str:
        return f"""
        Qdrant: {self.qdrant}
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