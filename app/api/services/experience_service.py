from typing import Dict, Any
from qdrant_client import AsyncQdrantClient, models
from app.databases.vectordb_factory import VectorDBFactory
from app.agent.azure_ai.factory import AzureAIFactory
from app.agent.core.files.db.embedding import Embedding
from ..schemas.experience_schema import MessageResponse
from app.config.settings import _settings

_embedding = Embedding(AzureAIFactory.create_resource("async_openai_embedding_3_large"))

async def check_experience_exists(experience_id: str) -> bool:
    
    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    count_points = await qdrant_client.count(
        collection_name=_settings.qdrant.experience_collection,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(key="experience_id", match=models.MatchValue(value=experience_id))
            ]
        )
    )
    return count_points.count > 0

async def upsert_experience(experience_id: str, payload: Dict[str, Any]) -> MessageResponse:
    
    content = f"""
    Error Title: {payload["error_title"]}
    Error Code: {payload["error_code"]}
    Device: {payload["device"]}
    Serial Number: {payload["serial_number"]}
    Priority: {payload["priority"]}
    Severity: {payload["severity"]}
    Occurred At: {payload["occurred_at"]}
    Error Component: {payload["error_component"]}
    Symptoms: {payload["symptoms"]}
    Firmware Version: {payload["firmware_version"]}
    Steps to Reproduce: {payload["steps_to_reproduce"]}
    Root Cause: {payload["root_cause"]}
    Workaround: {payload["workaround"]}
    Resolution Steps: {payload["resolution_steps"]}
    Time Spent (minutes): {payload["time_spent_mins"]}
    Material Cost Used: {payload["material_cost_used"]} 
    """
    
    dense_embedding, sparse_embedding = await _embedding.embed_document(content)
    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    
    payload = {**payload, "content": content, "experience_id": experience_id}
    point = models.PointStruct(
        id=experience_id,
        vector={
            "openai-embedding": dense_embedding,
            "bm25": sparse_embedding
        },
        payload=payload
    )
    await qdrant_client.upsert(
        collection_name=_settings.qdrant.experience_collection,
        points=[point]
    )
    
    message = MessageResponse(status="success", message="Experience updated successfully")
    return message

async def update_experience_by_id(experience_id: str, payload: Dict[str, Any]) -> MessageResponse:
    if not await check_experience_exists(experience_id):
        message = MessageResponse(status="failed", message="Experience not found")
        return message
    await delete_experience_by_id(experience_id)
    await upsert_experience(experience_id, payload)
    message = MessageResponse(status="success", message="Experience updated successfully")
    return message

async def delete_experience_by_id(experience_id: str) -> MessageResponse:
    if not await check_experience_exists(experience_id):
        message = MessageResponse(status="failed", message="Experience not found")
        return message
    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    await qdrant_client.delete(
        collection_name=_settings.qdrant.experience_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="experience_id",
                        match=models.MatchValue(value=experience_id),
                    )
                ]
            )
        ),
    )
    message = MessageResponse(status="success", message="Experience deleted successfully")
    return message


