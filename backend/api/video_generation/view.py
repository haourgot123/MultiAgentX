from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.video_generation.model import (
    VideoGenerationJobResponse,
    VideoGenerationRequest,
    VideoGenerationUpdateRequest,
)
from backend.api.video_generation.service import video_generation_service
from backend.utils.dependency import get_current_user, get_db


router = APIRouter(
    prefix="/video-generations",
    tags=["Video Generations"],
    dependencies=[Depends(get_current_user)],
)

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get(
    "",
    response_model=list[VideoGenerationJobResponse],
    status_code=status.HTTP_200_OK,
)
def list_video_generations(
    request: Request,
    db_session: Session = Depends(get_db),
):
    return video_generation_service.list_jobs(
        request,
        db_session,
        request.state.user_id,
    )


@router.get(
    "/{job_id}",
    response_model=VideoGenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def get_video_generation(
    request: Request,
    job_id: int,
    db_session: Session = Depends(get_db),
):
    return video_generation_service.get_job(
        request,
        db_session,
        request.state.user_id,
        job_id,
    )


@router.patch(
    "/{job_id}",
    response_model=VideoGenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
def update_video_generation(
    request: Request,
    job_id: int,
    update_request: VideoGenerationUpdateRequest,
    db_session: Session = Depends(get_db),
):
    return video_generation_service.update_job(
        request,
        db_session,
        request.state.user_id,
        job_id,
        update_request,
    )


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
def delete_video_generation(
    request: Request,
    job_id: int,
    db_session: Session = Depends(get_db),
):
    return video_generation_service.delete_job(
        request,
        db_session,
        request.state.user_id,
        job_id,
    )


@router.post("/render", status_code=status.HTTP_201_CREATED)
async def render_video(
    request: Request,
    render_request: VideoGenerationRequest,
    db_session: Session = Depends(get_db),
):
    return StreamingResponse(
        video_generation_service.render_stream(
            request,
            db_session,
            request.state.user_id,
            render_request,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
        status_code=status.HTTP_201_CREATED,
    )
