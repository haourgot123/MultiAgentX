from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.orm import Session

from backend.api.data_ingestion.model import (
    IngestionChunkListResponse,
    IngestionChunkRecordResponse,
    MilvusCollectionInfoResponse,
    IngestionRunRequest,
    IngestionRunResponse,
    IngestionStatusResponse,
)
from backend.api.data_ingestion.service import data_ingestion_service
from backend.exceptions.model import InvalidRequestException
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/ingestion",
    tags=["Data Ingestion"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/files/{file_id}/status",
    response_model=IngestionStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_file_ingestion_status(
    request: Request,
    file_id: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    stored_file = data_ingestion_service.get_ingestion_status(
        request, db_session, user_id, file_id
    )
    return IngestionStatusResponse(
        file_id=stored_file.id,
        status=stored_file.ingestion_status,
        error=stored_file.ingestion_error,
        chunks=stored_file.ingested_chunks,
        ingested_at=stored_file.ingested_at,
        updated_at=stored_file.updated_at,
    )


@router.post(
    "/files/{file_id}/run",
    response_model=IngestionRunResponse,
    status_code=status.HTTP_200_OK,
)
def run_file_ingestion(
    request: Request,
    file_id: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    return data_ingestion_service.ingest_file(request, db_session, user_id, file_id)


@router.post(
    "/files/run",
    response_model=list[IngestionRunResponse],
    status_code=status.HTTP_200_OK,
)
def run_files_ingestion(
    request: Request,
    payload: IngestionRunRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    return data_ingestion_service.ingest_files(
        request, db_session, user_id, payload.file_ids
    )


@router.get(
    "/collections",
    response_model=list[MilvusCollectionInfoResponse],
    status_code=status.HTTP_200_OK,
)
def list_ingestion_collections(request: Request):
    _ = request.state.user_id
    collections = data_ingestion_service.list_milvus_collections(request)
    return [MilvusCollectionInfoResponse(**collection) for collection in collections]


@router.get(
    "/chunks",
    response_model=IngestionChunkListResponse,
    status_code=status.HTTP_200_OK,
)
def list_ingestion_chunks(
    request: Request,
    user_id: int | None = Query(
        default=None,
        description="Filter chunks by user id. Defaults to current user.",
    ),
    file_id: int | None = Query(default=None, description="Optional file id filter"),
    limit: int = Query(default=50, ge=1, le=500, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
):
    current_user_id = request.state.user_id
    target_user_id = current_user_id if user_id is None else user_id
    if target_user_id != current_user_id:
        raise InvalidRequestException(message="Cannot query chunks for another user")

    items, has_more = data_ingestion_service.list_chunks(
        request=request,
        user_id=target_user_id,
        file_id=file_id,
        limit=limit,
        offset=offset,
    )
    return IngestionChunkListResponse(
        collection_name=data_ingestion_service.collection_name,
        user_id=target_user_id,
        file_id=file_id,
        limit=limit,
        offset=offset,
        has_more=has_more,
        items=[IngestionChunkRecordResponse(**item) for item in items],
    )


@router.get(
    "/files/{file_id}/chunks",
    response_model=IngestionChunkListResponse,
    status_code=status.HTTP_200_OK,
)
def list_file_chunks(
    request: Request,
    file_id: int,
    limit: int = Query(default=50, ge=1, le=500, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset"),
):
    current_user_id = request.state.user_id
    items, has_more = data_ingestion_service.list_chunks(
        request=request,
        user_id=current_user_id,
        file_id=file_id,
        limit=limit,
        offset=offset,
    )
    return IngestionChunkListResponse(
        collection_name=data_ingestion_service.collection_name,
        user_id=current_user_id,
        file_id=file_id,
        limit=limit,
        offset=offset,
        has_more=has_more,
        items=[IngestionChunkRecordResponse(**item) for item in items],
    )
