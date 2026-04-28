from langchain_openai.chat_models import AzureChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from backend.config.settings import _settings

azure_chat_openai_gpt_5_1 = AzureChatOpenAI(
    api_key=_settings.azure_chat_openai.api_key,
    api_version=_settings.azure_chat_openai.api_version,
    azure_endpoint=_settings.azure_chat_openai.api_endpoint,
    azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_5_1,
    temperature=_settings.azure_chat_openai.temperature,
    top_p=1.0,
    n=1,
    presence_penalty=0.0,
    frequency_penalty=0.0
)

try:
    azure_openai_embeddings = AzureOpenAIEmbeddings(
        api_key=_settings.openai_embedding.api_key,
        api_version=_settings.openai_embedding.api_version,
        azure_endpoint=_settings.openai_embedding.endpoint,
        azure_deployment=_settings.openai_embedding.embedding_model,
        dimensions=_settings.openai_embedding.embedding_dimension,
    )
except Exception:
    azure_openai_embeddings = None
