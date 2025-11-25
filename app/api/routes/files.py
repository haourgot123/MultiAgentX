from fastapi import APIRouter, status
from typing import List
from ..services.file_service import (
    upload_files_to_knowledge_base, 
    get_knowledge_bases,
    delete_file_by_id,
    delete_knowledge_base_by_id
)

from ..schemas.file_schemna import (
    UploadFileRequest, 
    UploadFileResponse,
    MessageResponse,
    CollectionName,
    FileSchema
)


router = APIRouter(prefix="/collections", tags=["Collections"])

@router.get("/", status_code=status.HTTP_200_OK, description="List all knowledge bases in a collection")
async def list_knowledge_bases() -> List[str]:
    response = get_knowledge_bases()
    return response

@router.post("/{collection_name}/knowledge-bases/{id}/files", status_code=status.HTTP_200_OK, description="Upload a file to a knowledge base")
async def upload_file_to_knowledge_base(
    collection_name: CollectionName,
    id: str,
    request: UploadFileRequest,
) -> UploadFileResponse:
    response = await upload_files_to_knowledge_base(collection_name, id, request.files)
    return response

@router.delete("/{collection_name}/knowledge-bases/{id}/files/{file_id}", status_code=status.HTTP_200_OK, description="Delete a file from a knowledge base")
async def delete_file_from_knowledge_base(
    collection_name: CollectionName,
    id: str,
    file_id: str,
) -> MessageResponse:
    response = await delete_file_by_id(collection_name, id, file_id)
    return response


@router.delete("/{collection_name}/knowledge-bases/{id}", status_code=status.HTTP_200_OK, description="Delete a knowledge base")
async def delete_knowledge_base(
    collection_name: CollectionName,
    id: str,
) -> MessageResponse:
    response = await delete_knowledge_base_by_id(collection_name, id)
    return response