from typing import List, Dict, Any
from ..schemas.file_schemna import (
    UploadFileResponse, 
    CollectionName,
    MessageResponse,
    FileSchema
)
from app.agent.core.files.tasks import process_file
from qdrant_client import models
from app.databases.vectordb_factory import VectorDBFactory

def get_knowledge_bases() -> List[str]:
    return [c.value for c in CollectionName]

async def check_field_value_exists(
    collection_name: str,
    field_name: str,
    field_value: str
) -> bool:
    
    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    count_points = await qdrant_client.count(
        collection_name=collection_name, 
        count_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key=field_name,
                    match=models.MatchValue(value=field_value)
                )
            ]
        )
    )
    return count_points.count > 0

async def upload_files_to_knowledge_base(
    collection_name: str,
    kb_id: str,
    files: List[FileSchema]
) -> UploadFileResponse:
    files = [file.model_dump() for file in files]
    task = process_file.apply_async(args=[kb_id, collection_name, files])
    return UploadFileResponse(
        task_id=task.id,
        message="File uploaded successfully"
    )
    

async def delete_file_by_id(
    collection_name: str,
    kb_id: str,
    file_id: str
) -> MessageResponse:
    
    # Check collection name exists
    if collection_name not in get_knowledge_bases():
        return MessageResponse(
            status="failed",
            message="Collection name not found"
        )
    # Check knowledge base exists
    if not await check_field_value_exists(collection_name, "knowledge_base_id", kb_id):
        return MessageResponse(
            status="failed",
            message="Knowledge base not found"
        )
    # Check file exists
    if not await check_field_value_exists(collection_name, "file_id", file_id):
        return MessageResponse(
            status="failed",
            message="File not found"
        )

    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    await qdrant_client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="file_id",
                    match=models.MatchValue(value=file_id)
                ),
                models.FieldCondition(
                    key="knowledge_base_id",
                    match=models.MatchValue(value=kb_id)
                )
            ]
        ))
    )
    return MessageResponse(
        status="success",
        message="File deleted successfully"
    )


async def delete_knowledge_base_by_id(
    collection_name: str,
    kb_id: str
) -> MessageResponse:
    if collection_name not in get_knowledge_bases():
        return MessageResponse(
            status="failed",
            message="Collection name not found"
        )
    if not await check_field_value_exists(collection_name, "knowledge_base_id", kb_id):
        return MessageResponse(
        status="failed",
        message="Knowledge base not found"
    )
    qdrant_client = VectorDBFactory.create_resource("async_qdrant")
    await qdrant_client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="knowledge_base_id",
                    match=models.MatchValue(value=kb_id)
                )
            ]
        ))
    )
    return MessageResponse(
        status="success",
        message="Knowledge base deleted successfully"
    )