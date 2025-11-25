from loguru import logger
from qdrant_client import models
from fastembed.sparse.bm25 import Bm25
from databases.vectordb_factory import VectorDBFactory
from app.agent.azure_ai.factory import AzureAIFactory
from .model import RetrieverModel, RetrieverModelResponse
from app.config.settings import _settings


class Retriever:

    def __init__(
        self,
        embedding_model: str = _settings.embedding_model.dense_model,
        sparse_model: str = _settings.embedding_model.sparse_model,
        qdrant_host: str = _settings.qdrant.qdrant_host,
        qdrant_port: str = _settings.qdrant.qdrant_port,
        threshold: float = 0.4
    ) -> None:
        
        self.sparse_embedding_model = Bm25(
            model_name=sparse_model
        )
        self.embedding_model = embedding_model
        self.threshold = threshold
        
    def invoke(
        self,
        input: RetrieverModel
    ) -> RetrieverModelResponse:
        embedding_model = AzureAIFactory.create_resource("openai_embedding_3_large")
        qdrant_client = VectorDBFactory.create_resource("qdrant")
        dense_embedding_response = embedding_model.embeddings.create(
            input=input.query,
            model=self.embedding_model
        )
        dense_embeddings_query = dense_embedding_response.data[0].embedding

        # Create sparse embeddings
        bm25_embeddings_query = next(self.sparse_embedding_model.query_embed(input.query))
        

        prefetch = [
            models.Prefetch(
                query=dense_embeddings_query,
                using="openai-embedding",
                limit=3
            ),

            models.Prefetch(
                query=models.SparseVector(**bm25_embeddings_query.as_object()),
                using="bm25",
                limit=3
            )
        ]

        responses = qdrant_client.query_points(
            collection_name=input.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            with_payload=True,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_base_id",
                        match=models.MatchAny(
                            any=input.kb_ids
                        )
                    )
                ]
            ),
            limit=input.limit,
        )

        final_response = []
        for response in responses.points:
            if response.score >= self.threshold:
                final_response.append(response.payload)

        return RetrieverModelResponse(results=final_response)
    

    async def ainvoke(
        self,
        input: RetrieverModel
    ) -> RetrieverModelResponse:

        embedding_model = AzureAIFactory.create_resource("async_openai_embedding_3_large")
        qdrant_client = VectorDBFactory.create_resource("async_qdrant")
        dense_embedding_response = await embedding_model.embeddings.create(
            input=input.query,
            model=self.embedding_model
        )
        dense_embeddings_query = dense_embedding_response.data[0].embedding

        # Create sparse embeddings
        bm25_embeddings_query = next(self.sparse_embedding_model.query_embed(input.query))
        

        prefetch = [
            models.Prefetch(
                query=dense_embeddings_query,
                using="openai-embedding",
                limit=3
            ),

            models.Prefetch(
                query=models.SparseVector(**bm25_embeddings_query.as_object()),
                using="bm25",
                limit=3
            )
        ]

        responses = await qdrant_client.query_points(
            collection_name=input.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            with_payload=True,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_base_id",
                        match=models.MatchAny(
                            any=input.kb_ids
                        )
                    )
                ]
            ),
            limit=input.limit,
        )

        final_response = []
        for response in responses.points:
            if response.score >= self.threshold:
                final_response.append(response.payload)

        return RetrieverModelResponse(results=final_response)


