from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.orm import Session

from backend.api.data_ingestion.model import (
    IngestionRunRequest,
    IngestionRunResponse,
    IngestionStatusResponse,
)
from backend.api.data_ingestion.service import data_ingestion_service
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
    stored_file = data_ingestion_service.get_ingestion_status(db_session, user_id, file_id)
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
    return data_ingestion_service.ingest_file(db_session, user_id, file_id)


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
    return data_ingestion_service.ingest_files(db_session, user_id, payload.file_ids)
