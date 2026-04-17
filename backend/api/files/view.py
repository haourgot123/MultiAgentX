from fastapi import APIRouter, Body, Depends, File, UploadFile, status
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from backend.api.files.model import (
    FileRenameRequest,
    FileResponse,
    FileSasResponse,
    SasUrlRequest,
)
from backend.api.files.service import file_service
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)]
)


def _to_file_response(stored_file, request: Request) -> FileResponse:
    """Build a FileResponse with a fresh SAS URL."""
    sas_url = file_service.get_sas_url(stored_file)
    return FileResponse(
        id=stored_file.id,
        name=stored_file.name,
        sas_url=sas_url,
        mime_type=stored_file.mime_type,
        size=stored_file.size,
        ingestion_status=stored_file.ingestion_status,
        ingestion_error=stored_file.ingestion_error,
        ingested_chunks=stored_file.ingested_chunks,
        ingested_at=stored_file.ingested_at,
        created_at=stored_file.created_at,
        updated_at=stored_file.updated_at,
    )


@router.get("", response_model=list[FileResponse], status_code=status.HTTP_200_OK)
def get_files(request: Request, db_session: Session = Depends(get_db)):
    user_id = request.state.user_id
    files = file_service.list_files(request, db_session, user_id)
    return [_to_file_response(f, request) for f in files]


@router.post(
    "/upload", response_model=list[FileResponse], status_code=status.HTTP_201_CREATED
)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    stored_files = await file_service.upload_files(request, db_session, user_id, files)
    return [_to_file_response(f, request) for f in stored_files]


@router.patch(
    "/{file_id}", response_model=FileResponse, status_code=status.HTTP_200_OK
)
def rename_file(
    request: Request,
    file_id: int,
    rename_request: FileRenameRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    stored_file = file_service.rename_file(
        request, db_session, user_id, file_id, rename_request.name
    )
    return _to_file_response(stored_file, request)


@router.get("/{file_id}/sas", response_model=FileSasResponse, status_code=status.HTTP_200_OK)
def get_file_sas(
    request: Request, file_id: int, db_session: Session = Depends(get_db)
):
    """Generate a fresh SAS URL for an individual file."""
    user_id = request.state.user_id
    stored_file = file_service.get_file(request, db_session, user_id, file_id)
    sas_url = file_service.get_sas_url(stored_file)
    expires_at = file_service.get_sas_expiry()
    return FileSasResponse(sas_url=sas_url, expires_at=expires_at)


@router.post("/sas", status_code=status.HTTP_200_OK)
def get_files_sas_batch(
    request: Request,
    body: SasUrlRequest,
    db_session: Session = Depends(get_db),
):
    """Generate fresh SAS URLs for multiple files in one request."""
    user_id = request.state.user_id
    result: dict[str, str] = {}
    for file_id in body.file_ids:
        try:
            stored_file = file_service.get_file(request, db_session, user_id, file_id)
            result[str(file_id)] = file_service.get_sas_url(stored_file)
        except Exception:
            # Skip files that cannot be found / accessed
            pass
    expires_at = file_service.get_sas_expiry()
    return {"urls": result, "expires_at": expires_at}


@router.get("/{file_id}/download", status_code=status.HTTP_302_FOUND)
def download_file(
    request: Request, file_id: int, db_session: Session = Depends(get_db)
):
    """Redirect to a short-lived SAS URL for the file (download)."""
    user_id = request.state.user_id
    stored_file = file_service.get_file(request, db_session, user_id, file_id)
    sas_url = file_service.get_sas_url(stored_file)
    return RedirectResponse(url=sas_url, status_code=status.HTTP_302_FOUND)


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(
    request: Request, file_id: int, db_session: Session = Depends(get_db)
):
    user_id = request.state.user_id
    response = file_service.delete_file(request, db_session, user_id, file_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)
