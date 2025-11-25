from typing import Dict, Any
from app.config.settings import _settings
from openai import AzureOpenAI, AsyncAzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from langchain_openai import AzureChatOpenAI

class AzureAIFactory:
    _azure_resources_registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, creator):
        cls._azure_resources_registry[name] = creator

    @classmethod
    def create_resource(cls, name: str):
        creator = cls._azure_resources_registry.get(name)
        if not creator:
            raise ValueError(f"No resource named '{name}' registered.")
        return creator()        
    
    @classmethod
    def create_async_chat_azopenai_4_1(cls):
        return AsyncAzureOpenAI(
            azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_4_1,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        
    @classmethod
    def create_async_chat_azopenai_4_1_mini(cls):
        return AsyncAzureOpenAI(
            azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_4_1_mini,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        
        
    @classmethod
    def create_chat_azopenai_4_1(cls):
        return AzureOpenAI(
            azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_4_1,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        
    @classmethod
    def create_chat_azopenai_4_1_mini(cls):
        return AzureOpenAI(
            azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_4_1_mini,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
    
    @classmethod
    def create_openai_embedding_3_large(cls):
        return AzureOpenAI(
            azure_deployment=_settings.embedding_model.dense_model,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        
    @classmethod
    def create_async_openai_embedding_3_large(cls):
        return AsyncAzureOpenAI(
            azure_deployment=_settings.embedding_model.dense_model,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        
    @classmethod
    def create_document_intelligence_client(cls):
        return DocumentIntelligenceClient(
            endpoint=_settings.azure_document_intelligence.api_endpoint,
            credential=AzureKeyCredential(_settings.azure_document_intelligence.api_key),
            headers={"x-ms-useragent": "sample-code-merge-cross-tables/1.0.0"},
            api_version="2024-11-30",
        )
    
    @classmethod
    def create_langchain_azure_chat_openai_4_1(cls):
        return AzureChatOpenAI(
            azure_deployment=_settings.azure_chat_openai.deployment_name_gpt_4_1,
            api_version=_settings.azure_chat_openai.api_version,
            api_key=_settings.azure_chat_openai.api_key,
            azure_endpoint=_settings.azure_chat_openai.api_endpoint,
        )
        

AzureAIFactory.register("chat_azopenai_4_1", AzureAIFactory.create_chat_azopenai_4_1)
AzureAIFactory.register("async_chat_azopenai_4_1", AzureAIFactory.create_async_chat_azopenai_4_1)
AzureAIFactory.register("chat_azopenai_4_1_mini", AzureAIFactory.create_chat_azopenai_4_1_mini)
AzureAIFactory.register("async_chat_azopenai_4_1_mini", AzureAIFactory.create_async_chat_azopenai_4_1_mini)
AzureAIFactory.register("document_intelligence", AzureAIFactory.create_document_intelligence_client)
AzureAIFactory.register("openai_embedding_3_large", AzureAIFactory.create_openai_embedding_3_large)
AzureAIFactory.register("async_openai_embedding_3_large", AzureAIFactory.create_async_openai_embedding_3_large)
AzureAIFactory.register("langchain_azure_chat_openai_4_1", AzureAIFactory.create_langchain_azure_chat_openai_4_1)
