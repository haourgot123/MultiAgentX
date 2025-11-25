import os
from loguru import logger
import tqdm
from typing import List, Dict, Any, Generator
from app.config.settings import _settings
from typing import Any
from qdrant_client import models


def batch_creater(
    documents: List[Dict[str, Any]],
    batch_size: int = _settings.qdrant.qdrant_batch_size
) -> Generator[List[Dict[str, Any]], None, None]:
    for i in range(0, len(documents), batch_size):
        yield documents[i:i + batch_size]

class Indexing:
    def __init__(self, qdrant_client: Any):
        self.qdrant_client = qdrant_client
    
    def create_collection(
        self,
        collection_name: str
    ):
        
        dense_vector_config = {
            "openai-embedding": models.VectorParams(
                size=_settings.embedding_model.dense_embedding_size,
                distance=models.Distance.COSINE
            )
        }
        
        sparse_vector_config = {
            'bm25': models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        }

        if not self.qdrant_client.collection_exists(collection_name):
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=dense_vector_config,
                sparse_vectors_config=sparse_vector_config
            )
            logger.info(f"Collection {collection_name} created successfully")
        else:
            logger.info(f"Collection {collection_name} already exists")
            
    
    async def index_documents_batch(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        batch_size: int = _settings.qdrant.qdrant_batch_size
    ):
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for idx, batch in enumerate(tqdm.tqdm(
            batch_creater(documents, batch_size=batch_size),
            total=total_batches,
            desc="Indexing documents"
        ), 1):
            batch_metadata = [doc['payload'] for doc in batch]
            batch_vectors = [doc['vector'] for doc in batch]

            batch_points = [
                models.PointStruct(
                    id=batch_metadata[i]['document_id'],
                    vector=batch_vectors[i],
                    payload=batch_metadata[i]
                )
                for i in range(len(batch_metadata))
            ]
            
            await self.qdrant_client.upsert(collection_name=collection_name, points=batch_points)
            logger.info(f"Documents indexed successfully for batch {idx}/{total_batches}")