from urllib.parse import urlparse
import io
import uuid

import httpx
from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.general_agent.tools.websearch import (
    SearchRequest,
    TavilySearchService,
)
from backend.agents.video_generation_agent.state import VideoGenerationAgentState
from backend.utils.blob_storage import blob_storage_client


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
service_logger = logger.bind(service="video-assets")


class AssetNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    @staticmethod
    def _is_image_url(url: str) -> bool:
        path = urlparse(url).path.lower()
        return url.startswith(("http://", "https://")) and (
            any(path.endswith(ext) for ext in IMAGE_EXTENSIONS) or not path
        )

    @staticmethod
    def _dedupe_urls(urls: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for url in urls:
            normalized = (url or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _collect_source_images(self, state: VideoGenerationAgentState) -> list[str]:
        urls: list[str] = []
        for source in state.sources:
            urls.extend(source.images)
            if self._is_image_url(source.url):
                urls.append(source.url)
        return self._dedupe_urls([url for url in urls if self._is_image_url(url)])

    async def _search_scene_images(self, state: VideoGenerationAgentState) -> list[str]:
        if not state.web_search_enabled:
            return []

        search_service = TavilySearchService()
        urls: list[str] = []
        for scene in state.storyboard[:5]:
            query = f"{scene.visual_prompt or scene.title} high quality visual reference"
            try:
                results = await search_service.search(
                    SearchRequest(
                        query=query,
                        total_results=2,
                        include_images=True,
                        include_image_descriptions=True,
                    )
                )
                for result in results:
                    urls.extend(result.images)
                    if self._is_image_url(result.url):
                        urls.append(result.url)
            except Exception as exc:
                service_logger.warning("Scene image search failed query={}: {}", query, exc)

        return self._dedupe_urls([url for url in urls if self._is_image_url(url)])

    async def _mirror_image_to_blob(self, url: str, user_id: int, job_id: int) -> str | None:
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                verify=False,
                headers={"User-Agent": "MultiAgentX-VideoRenderer/1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                return None
            if len(response.content) > MAX_IMAGE_BYTES:
                return None

            extension = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }[content_type]
            blob_path = (
                f"video-generations/{user_id}/{job_id}/assets/"
                f"{uuid.uuid4().hex}.{extension}"
            )
            blob_storage_client.upload_bytes(
                blob_path=blob_path,
                data=io.BytesIO(response.content),
                content_type=content_type,
            )
            return blob_storage_client.generate_sas_url(blob_path, expiry_hours=24)
        except Exception as exc:
            service_logger.debug("Unable to mirror image url={} error={}", url, exc)
            return None

    async def _prepare_image_urls(self, state: VideoGenerationAgentState) -> list[str]:
        candidate_urls = self._collect_source_images(state)
        if len(candidate_urls) < len(state.storyboard):
            candidate_urls.extend(await self._search_scene_images(state))

        prepared_urls: list[str] = []
        for url in self._dedupe_urls(candidate_urls)[: max(len(state.storyboard) * 2, 6)]:
            mirrored_url = await self._mirror_image_to_blob(url, state.user_id, state.job_id)
            prepared_urls.append(mirrored_url or url)
            if len(prepared_urls) >= len(state.storyboard):
                break

        return prepared_urls

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "assets",
                "message": "Searching and preparing visual assets...",
            },
        )

        image_urls = await self._prepare_image_urls(state)
        dispatch_custom_event(
            "status",
            {
                "step": "assets",
                "message": f"Prepared {len(image_urls)} visual reference(s).",
            },
        )

        scenes = []
        for index, scene in enumerate(state.storyboard):
            image_url = image_urls[index % len(image_urls)] if image_urls else None
            scenes.append(scene.model_copy(update={"image_url": image_url}))

        return {"storyboard": scenes}
