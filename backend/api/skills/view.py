from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, RedirectResponse

from backend.api.skills.model import (
    SkillResponse,
    SkillUpdateRequest,
    SandboxResponse,
    SkillExecutionRequest,
    SkillSelectRequest,
)
from backend.api.skills.service import skill_service, sandbox_service
from backend.utils.blob_storage import blob_storage_client
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/skills", tags=["Skills"], dependencies=[Depends(get_current_user)]
)

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _to_skill_response(skill) -> SkillResponse:
    download_url: str | None = None
    if skill.blob_path:
        try:
            download_url = blob_storage_client.generate_sas_url(skill.blob_path)
        except Exception:
            download_url = None
    return SkillResponse(
        id=skill.id,
        user_id=skill.user_id,
        name=skill.name,
        description=skill.description,
        storage_path=skill.storage_path,
        allowed_tools=skill.allowed_tools,
        file_type=skill.file_type,
        is_active=skill.is_active,
        is_selected=skill.is_selected,
        size=skill.size,
        download_url=download_url,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


def _to_sandbox_response(sandbox) -> SandboxResponse:
    return SandboxResponse(
        id=sandbox.id,
        sandbox_index=sandbox.sandbox_index,
        status=sandbox.status,
        current_skill_id=sandbox.current_skill_id,
        task_description=sandbox.task_description,
        progress=sandbox.progress,
        started_at=sandbox.started_at,
        completed_at=sandbox.completed_at,
    )


@router.get("", response_model=List[SkillResponse], status_code=status.HTTP_200_OK)
def list_skills(request: Request, db_session: Session = Depends(get_db)):
    user_id = request.state.user_id
    skills = skill_service.list_skills(request, db_session, user_id)
    return [_to_skill_response(skill) for skill in skills]


@router.post(
    "/upload", response_model=SkillResponse, status_code=status.HTTP_201_CREATED
)
async def upload_skill(
    request: Request,
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    skill = await skill_service.upload_skill(request, db_session, user_id, file)
    return _to_skill_response(skill)


@router.get("/{skill_id}/download", status_code=status.HTTP_302_FOUND)
def download_skill(
    request: Request, skill_id: int, db_session: Session = Depends(get_db)
):
    user_id = request.state.user_id
    skill = skill_service.get_skill(request, db_session, user_id, skill_id)
    if skill.blob_path:
        sas_url = blob_storage_client.generate_sas_url(skill.blob_path)
        return RedirectResponse(url=sas_url, status_code=302)
    # Fallback: skill predates blob storage — not available for download
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Download not available for this skill")


@router.patch(
    "/{skill_id}", response_model=SkillResponse, status_code=status.HTTP_200_OK
)
def update_skill(
    request: Request,
    skill_id: int,
    update_request: SkillUpdateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    skill = skill_service.update_skill(
        request, db_session, user_id, skill_id, update_request
    )
    return _to_skill_response(skill)


@router.delete("/{skill_id}", status_code=status.HTTP_200_OK)
def delete_skill(
    request: Request, skill_id: int, db_session: Session = Depends(get_db)
):
    user_id = request.state.user_id
    response = skill_service.delete_skill(request, db_session, user_id, skill_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@router.post("/select", response_model=SkillResponse, status_code=status.HTTP_200_OK)
def toggle_skill_selection(
    request: Request,
    select_request: SkillSelectRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    skill = skill_service.toggle_skill_selection(
        request, db_session, user_id, select_request.skill_id, select_request.is_selected
    )
    return _to_skill_response(skill)


@router.get(
    "/sandboxes/list",
    response_model=List[SandboxResponse],
    status_code=status.HTTP_200_OK,
)
def list_sandboxes(request: Request, db_session: Session = Depends(get_db)):
    user_id = request.state.user_id
    sandboxes = sandbox_service.list_sandboxes(request, db_session, user_id)
    return [_to_sandbox_response(sandbox) for sandbox in sandboxes]


@router.get("/sandboxes/{sandbox_index}/files", status_code=status.HTTP_200_OK)
def list_sandbox_files(
    request: Request,
    sandbox_index: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    files = sandbox_service.docker_manager.list_output_files(user_id, sandbox_index)
    return {"files": files}


@router.get("/sandboxes/{sandbox_index}/files/{filename}/preview", status_code=status.HTTP_200_OK)
def preview_sandbox_file(
    request: Request,
    sandbox_index: int,
    filename: str,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or ".." in filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid filename"}
        )
    file_path = sandbox_service.docker_manager.get_output_file(user_id, sandbox_index, safe_name)
    if not file_path:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "File not found"}
        )

    ext = Path(filename).suffix.lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".json": "application/json",
        ".csv": "text/csv",
        ".html": "text/html",
        ".js": "application/javascript",
        ".py": "text/x-python",
    }
    media_type = mime_types.get(ext, "application/octet-stream")

    return FastAPIFileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )


@router.get("/sandboxes/{sandbox_index}/files/{filename:path}", status_code=status.HTTP_200_OK)
def download_sandbox_file(
    request: Request,
    sandbox_index: int,
    filename: str,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or ".." in filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid filename"}
        )
    file_path = sandbox_service.docker_manager.get_output_file(user_id, sandbox_index, safe_name)
    if not file_path:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "File not found"}
        )
    return FastAPIFileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post("/execute", status_code=status.HTTP_200_OK)
async def execute_skills(
    request: Request,
    execution_request: SkillExecutionRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id

    async def event_generator():
        async for event in sandbox_service.execute_skill_stream(
            request,
            db_session,
            user_id,
            execution_request.skill_ids,
            execution_request.user_message,
            execution_request.conversation_id,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )