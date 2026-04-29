import json
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import Request
from loguru import logger
from sqlalchemy.orm import Session

from backend.agents.video_generation_agent.graph import VideoGenerationAgentGraph
from backend.agents.video_generation_agent.state import VideoGenerationAgentState
from backend.api.video_generation.model import (
    VideoGenerationJob,
    VideoGenerationJobResponse,
    VideoGenerationRequest,
    VideoGenerationUpdateRequest,
)
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.blob_storage import blob_storage_client
from backend.utils.retention import mark_for_retention_delete




class VideoGenerationService:
    STATUS_PROGRESS = {
        "validate": ("queued", 5),
        "research": ("researching", 20),
        "storyboard": ("storyboarding", 35),
        "assets": ("storyboarding", 50),
        "remotion_input": ("storyboarding", 60),
        "rendering": ("rendering", 75),
        "finalizing": ("rendering", 90),
    }

    @staticmethod
    def _format_sse_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return logger.bind(
            request_id=getattr(getattr(request, "state", None), "request_id", "-"),
            user_id=user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-"),
        )

    @staticmethod
    def _normalize_path(value: Any) -> Path | None:
        if not value:
            return None
        if isinstance(value, Path):
            return value
        return Path(str(value))

    def _validate_request(self, render_request: VideoGenerationRequest) -> None:
        max_duration = _settings.video_generation.max_duration_seconds
        if render_request.duration_seconds > max_duration:
            raise InvalidRequestException(
                message=f"Video duration cannot exceed {max_duration} seconds"
            )
        if render_request.duration_seconds * render_request.fps > max_duration * 30:
            raise InvalidRequestException(message="Video frame count exceeds the v1 limit")

    def _create_job(
        self,
        db_session: Session,
        user_id: int,
        render_request: VideoGenerationRequest,
    ) -> VideoGenerationJob:
        now = get_utc_now()
        job = VideoGenerationJob(
            user_id=user_id,
            title=render_request.prompt[:255],
            prompt=render_request.prompt,
            style=render_request.style,
            aspect_ratio=render_request.aspect_ratio,
            duration_seconds=render_request.duration_seconds,
            fps=render_request.fps,
            web_search_enabled=render_request.web_search_enabled,
            status="queued",
            progress=0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    def _get_user_job(
        self,
        db_session: Session,
        user_id: int,
        job_id: int,
        request_logger,
    ) -> VideoGenerationJob:
        job = (
            db_session.query(VideoGenerationJob)
            .filter(
                VideoGenerationJob.id == job_id,
                VideoGenerationJob.user_id == user_id,
                VideoGenerationJob.deleted_at.is_(None),
            )
            .first()
        )
        if not job:
            request_logger.warning("Video generation job not found id={}", job_id)
            raise ObjectNotFoundException(message="Video generation job not found")
        return job

    def _update_job(
        self,
        db_session: Session,
        job: VideoGenerationJob,
        *,
        status: str | None = None,
        progress: int | None = None,
        storyboard_json: Any | None = None,
        sources_json: Any | None = None,
        video_blob_path: str | None = None,
        thumbnail_blob_path: str | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> VideoGenerationJob:
        now = get_utc_now()
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if storyboard_json is not None:
            job.storyboard_json = storyboard_json
        if sources_json is not None:
            job.sources_json = sources_json
        if video_blob_path is not None:
            job.video_blob_path = video_blob_path
        if thumbnail_blob_path is not None:
            job.thumbnail_blob_path = thumbnail_blob_path
        if error_message is not None:
            job.error_message = error_message
        if completed:
            job.completed_at = now
        job.updated_at = now
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    def _upload_output(
        self,
        *,
        user_id: int,
        job_id: int,
        path: Path,
        suffix: str,
        content_type: str,
    ) -> str:
        blob_path = f"video-generations/{user_id}/{job_id}/{uuid.uuid4().hex}{suffix}"
        with path.open("rb") as file_data:
            return blob_storage_client.upload_bytes(
                blob_path=blob_path,
                data=file_data,
                content_type=content_type,
            )

    def _response_for_job(self, job: VideoGenerationJob) -> VideoGenerationJobResponse:
        video_url = None
        thumbnail_url = None
        try:
            if job.video_blob_path:
                video_url = blob_storage_client.generate_sas_url(
                    job.video_blob_path, expiry_hours=24
                )
            if job.thumbnail_blob_path:
                thumbnail_url = blob_storage_client.generate_sas_url(
                    job.thumbnail_blob_path, expiry_hours=24
                )
        except Exception as exc:
            logger.warning("[VideoGenerationService] Failed to generate video SAS URL: {}", exc)

        return VideoGenerationJobResponse(
            id=job.id,
            title=job.title or job.prompt[:255],
            prompt=job.prompt,
            style=job.style,
            aspect_ratio=job.aspect_ratio,
            duration_seconds=job.duration_seconds,
            fps=job.fps,
            web_search_enabled=job.web_search_enabled,
            status=job.status,
            progress=job.progress,
            storyboard=job.storyboard_json,
            sources=job.sources_json,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
        )

    def list_jobs(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
    ) -> list[VideoGenerationJobResponse]:
        _ = self._get_request_logger(request, user_id)
        jobs = (
            db_session.query(VideoGenerationJob)
            .filter(
                VideoGenerationJob.user_id == user_id,
                VideoGenerationJob.deleted_at.is_(None),
            )
            .order_by(VideoGenerationJob.created_at.desc())
            .all()
        )
        return [self._response_for_job(job) for job in jobs]

    def get_job(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        job_id: int,
    ) -> VideoGenerationJobResponse:
        request_logger = self._get_request_logger(request, user_id)
        job = self._get_user_job(db_session, user_id, job_id, request_logger)
        return self._response_for_job(job)

    def update_job(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        job_id: int,
        update_request: VideoGenerationUpdateRequest,
    ) -> VideoGenerationJobResponse:
        request_logger = self._get_request_logger(request, user_id)
        job = self._get_user_job(db_session, user_id, job_id, request_logger)
        job.title = update_request.title
        job.updated_at = get_utc_now()
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return self._response_for_job(job)

    def delete_job(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        job_id: int,
    ) -> dict:
        request_logger = self._get_request_logger(request, user_id)
        job = self._get_user_job(db_session, user_id, job_id, request_logger)
        mark_for_retention_delete(job)
        request_logger.info(
            "Soft deleted video generation job id={} purge_after={}",
            job.id,
            job.purge_after,
        )
        db_session.commit()

        return {"message": "Video generation deleted successfully"}

    async def render_stream(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        render_request: VideoGenerationRequest,
    ) -> AsyncGenerator[str, None]:
        request_logger = self._get_request_logger(request, user_id)
        self._validate_request(render_request)
        job = self._create_job(db_session, user_id, render_request)

        yield self._format_sse_event(
            "status",
            {
                "step": "queued",
                "message": "Video generation job queued.",
                "job_id": job.id,
            },
        )

        try:
            state = VideoGenerationAgentState(
                job_id=job.id,
                user_id=user_id,
                prompt=render_request.prompt,
                duration_seconds=render_request.duration_seconds,
                fps=render_request.fps,
                aspect_ratio=render_request.aspect_ratio,
                style=render_request.style,
                web_search_enabled=render_request.web_search_enabled,
            )
            graph = VideoGenerationAgentGraph()
            final_state: dict[str, Any] | None = None

            async for event in graph.stream(state.model_dump()):
                event_type = event.get("type")
                if event_type == "status":
                    step = event.get("step", "")
                    status, progress = self.STATUS_PROGRESS.get(
                        step,
                        (job.status, job.progress),
                    )
                    job = self._update_job(
                        db_session,
                        job,
                        status=status,
                        progress=progress,
                    )
                    yield self._format_sse_event(
                        "status",
                        {
                            "step": step,
                            "message": event.get("message", ""),
                            "job_id": job.id,
                        },
                    )
                elif event_type == "storyboard":
                    storyboard_payload = {"scenes": event.get("scenes", [])}
                    job = self._update_job(
                        db_session,
                        job,
                        status="storyboarding",
                        progress=45,
                        storyboard_json=storyboard_payload,
                    )
                    yield self._format_sse_event("storyboard", storyboard_payload)
                elif event_type == "result":
                    final_state = event.get("state") or {}

            if not final_state:
                raise RuntimeError("Video agent completed without a render result")

            video_path = self._normalize_path(final_state.get("video_path"))
            thumbnail_path = self._normalize_path(final_state.get("thumbnail_path"))
            if not video_path or not video_path.exists():
                raise RuntimeError("Rendered video file not found")

            video_blob_path = self._upload_output(
                user_id=user_id,
                job_id=job.id,
                path=video_path,
                suffix=".mp4",
                content_type="video/mp4",
            )
            thumbnail_blob_path = None
            if thumbnail_path and thumbnail_path.exists():
                thumbnail_blob_path = self._upload_output(
                    user_id=user_id,
                    job_id=job.id,
                    path=thumbnail_path,
                    suffix=".png",
                    content_type="image/png",
                )

            sources = final_state.get("sources", [])
            if sources and not isinstance(sources[0], dict):
                sources = [source.model_dump() for source in sources]

            job = self._update_job(
                db_session,
                job,
                status="completed",
                progress=100,
                sources_json=sources,
                video_blob_path=video_blob_path,
                thumbnail_blob_path=thumbnail_blob_path,
                completed=True,
            )
            response = self._response_for_job(job)
            yield self._format_sse_event(
                "video_result",
                {
                    "job_id": job.id,
                    "video_url": response.video_url,
                    "thumbnail_url": response.thumbnail_url,
                    "duration_seconds": job.duration_seconds,
                    "fps": job.fps,
                    "aspect_ratio": job.aspect_ratio,
                },
            )
            yield self._format_sse_event("done", {"job_id": job.id})

        except Exception as exc:
            request_logger.error("Video generation failed job_id={}: {}", job.id, exc)
            message = str(exc) or "Video generation failed"
            self._update_job(
                db_session,
                job,
                status="failed",
                progress=100,
                error_message=message,
                completed=True,
            )
            yield self._format_sse_event("error", {"message": message, "job_id": job.id})


video_generation_service = VideoGenerationService()
