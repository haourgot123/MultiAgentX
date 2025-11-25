import os 
import asyncio
import logging
from typing import List, Dict, Any
from app.config.settings import _settings
from fastembed.sparse.bm25 import Bm25
logger = logging.getLogger(__name__)

    
class Embedding:
    def __init__(self, dense_embedding_model: Any):
        self.dense_embedding_model = dense_embedding_model
        self.sparse_embedding_model = Bm25(model_name=_settings.embedding_model.sparse_model)
        
    async def embed_document(self, document_content: str):
        
        dense_embedding = await self.dense_embedding_model.embeddings.create(input=document_content, model = _settings.embedding_model.dense_model)
        sparse_embedding = await asyncio.to_thread(self.sparse_embedding_model.passage_embed, document_content)
        dense_embedding = list(dense_embedding.data[0].embedding)
        sparse_embedding = list(sparse_embedding)[0].as_object()
        return dense_embedding, sparse_embedding

    async def embed_documents(self, documents: List[Dict[str, Any]]):
        
        final_documents = []
        for document in documents:
            dense_embedding, sparse_embedding = await self.embed_document(document["payload"]["content"])
            final_documents.append(
                {
                    **document,
                    "vector": {
                        "openai-embedding": dense_embedding,
                        "bm25": sparse_embedding
                    }
                }
            )
        return final_documents
    
    async def embed_documents_batch(self, documents: List[Dict[str, Any]], batch_size: int = 10):
        
        final_documents = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_embedding_documents = await self.embed_documents(batch)
            final_documents.extend(batch_embedding_documents)
        return final_documents  