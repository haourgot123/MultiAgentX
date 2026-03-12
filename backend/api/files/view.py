from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.requests import Request
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from backend.api.files.model import FileRenameRequest, FileResponse
from backend.api.files.service import file_service
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[FileResponse], status_code=status.HTTP_200_OK)
def get_files(request: Request, db_session: Session = Depends(get_db)):
    user_id = request.state.user_id
    return file_service.list_files(request, db_session, user_id)


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
    return stored_files


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
    return file_service.rename_file(
        request, db_session, user_id, file_id, rename_request.name
    )


@router.get("/{file_id}/download", status_code=status.HTTP_200_OK)
def download_file(
    request: Request, file_id: int, db_session: Session = Depends(get_db)
):
    user_id = request.state.user_id
    file_info = file_service.get_file(request, db_session, user_id, file_id)
    return FastAPIFileResponse(
        path=file_info.storage_path,
        filename=file_info.name,
        media_type=file_info.mime_type,
    )


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(
    request: Request, file_id: int, db_session: Session = Depends(get_db)
):
    user_id = request.state.user_id
    response = file_service.delete_file(request, db_session, user_id, file_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)
