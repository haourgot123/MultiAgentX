import base64
import io
import re
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from PIL import Image
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from loguru import logger
from pydantic import BaseModel, Field

from backend.agents.general_agent.tools.websearch import (
    SearchRequest,
    TavilySearchService,
)
from backend.agents.video_generation_agent.state import (
    VideoGenerationAgentState,
    VideoScene,
)
from backend.utils.blob_storage import blob_storage_client
from backend.utils.llm import azure_chat_openai_gpt_5_1


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MIN_IMAGE_WIDTH = 960
MIN_IMAGE_HEIGHT = 540
MAX_CANDIDATES_PER_SCENE = 4
MAX_TAVILY_QUERY_LENGTH = 180
REJECT_URL_TOKENS = {
    "thumbnail",
    "sprite",
    "watermark",
    "poster",
    "infographic",
    "screenshot",
}


@dataclass(slots=True)
class CandidateImage:
    source_url: str
    content_type: str
    image_bytes: bytes
    width: int
    height: int
    review_data_url: str


class CandidateAssessment(BaseModel):
    index: int = Field(description="1-based candidate index")
    verdict: str = Field(description="Use 'accept' or 'reject'")
    quality_score: int = Field(description="0-100 score for visual quality")
    relevance_score: int = Field(description="0-100 score for fit to the requested scene")
    has_visible_text: bool = Field(description="True if visible text, caption, subtitle, or annotation appears")
    is_blurry: bool = Field(description="True if the image looks blurry, low-resolution, or soft")
    is_graphic_or_screenshot: bool = Field(
        description="True if this feels like a logo, poster, infographic, slide, UI screenshot, or thumbnail"
    )
    reason: str = Field(description="Short justification")


class SceneImageSelection(BaseModel):
    selected_index: int = Field(
        description="1-based chosen candidate index, or 0 if every candidate should be rejected"
    )
    overall_reason: str = Field(description="Short explanation for the final choice")
    assessments: list[CandidateAssessment] = Field(default_factory=list)


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

    @staticmethod
    def _should_reject_url(url: str) -> bool:
        normalized = url.lower()
        return any(token in normalized for token in REJECT_URL_TOKENS)

    def _collect_source_images(self, state: VideoGenerationAgentState) -> list[str]:
        urls: list[str] = []
        for source in state.sources:
            urls.extend(source.images)
            if self._is_image_url(source.url):
                urls.append(source.url)
        return self._dedupe_urls([url for url in urls if self._is_image_url(url)])

    @staticmethod
    def _condense_query_text(value: str, max_words: int) -> str:
        cleaned = re.sub(r"[^0-9A-Za-zÀ-ỹ\s-]", " ", value or "", flags=re.UNICODE)
        cleaned = re.sub(r"\s+", " ", cleaned, flags=re.UNICODE).strip()
        if not cleaned:
            return ""
        words = cleaned.split(" ")
        return " ".join(words[:max_words])

    def _build_scene_search_query(
        self,
        state: VideoGenerationAgentState,
        scene: VideoScene,
    ) -> str:
        parts = [
            self._condense_query_text(state.prompt, 6),
            self._condense_query_text(scene.title, 5),
            self._condense_query_text(scene.visual_motif, 5),
            self._condense_query_text(scene.visual_prompt, 8),
            "professional photo no text",
        ]
        query = " ".join(part for part in parts if part).strip()
        if len(query) <= MAX_TAVILY_QUERY_LENGTH:
            return query

        trimmed_parts = [
            self._condense_query_text(state.prompt, 5),
            self._condense_query_text(scene.title, 4),
            self._condense_query_text(scene.visual_motif, 4),
            "professional photo",
        ]
        query = " ".join(part for part in trimmed_parts if part).strip()
        return query[:MAX_TAVILY_QUERY_LENGTH].rstrip(" ,-")

    async def _search_scene_images(
        self,
        state: VideoGenerationAgentState,
        scene: VideoScene,
    ) -> list[str]:
        if not state.web_search_enabled:
            return []

        search_service = TavilySearchService()
        query = self._build_scene_search_query(state, scene)
        try:
            results = await search_service.search(
                SearchRequest(
                    query=query,
                    total_results=2,
                    include_images=True,
                    include_image_descriptions=False,
                    search_depth="basic",
                )
            )
        except Exception as exc:
            logger.warning(
                f"[VideoGenerationAgent (AssetNode)] Scene image search failed "
                f"scene={scene.index} query={query} error={exc}"
            )
            return []

        urls: list[str] = []
        for result in results:
            urls.extend(result.images)
            if self._is_image_url(result.url):
                urls.append(result.url)
        return self._dedupe_urls([url for url in urls if self._is_image_url(url)])

    @staticmethod
    def _make_review_data_url(image_bytes: bytes) -> str:
        with Image.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                raise ValueError(f"image too small {width}x{height}")

            preview = image.convert("RGB")
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            preview.thumbnail((768, 768), resampling)

            buffer = io.BytesIO()
            preview.save(buffer, format="JPEG", quality=84, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"

    async def _download_candidate(
        self,
        url: str,
        cache: dict[str, CandidateImage | None],
    ) -> CandidateImage | None:
        if url in cache:
            return cache[url]

        if self._should_reject_url(url):
            cache[url] = None
            return None

        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                verify=False,
                headers={"User-Agent": "MultiAgentX-VideoRenderer/1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception as exc:
            logger.debug(
                f"[VideoGenerationAgent (AssetNode)] Unable to download candidate image "
                f"url={url} error={exc}"
            )
            cache[url] = None
            return None

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            cache[url] = None
            return None
        if len(response.content) > MAX_IMAGE_BYTES:
            cache[url] = None
            return None

        try:
            with Image.open(io.BytesIO(response.content)) as image:
                width, height = image.size
            review_data_url = self._make_review_data_url(response.content)
        except Exception as exc:
            logger.debug(
                f"[VideoGenerationAgent (AssetNode)] Unable to prepare candidate image "
                f"url={url} error={exc}"
            )
            cache[url] = None
            return None

        candidate = CandidateImage(
            source_url=url,
            content_type=content_type,
            image_bytes=response.content,
            width=width,
            height=height,
            review_data_url=review_data_url,
        )
        cache[url] = candidate
        return candidate

    async def _review_scene_candidates(
        self,
        state: VideoGenerationAgentState,
        scene: VideoScene,
        candidates: list[CandidateImage],
    ) -> SceneImageSelection | None:
        if not candidates:
            return None

        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "You are a strict visual curator for a professional Remotion video. "
                    "Choose exactly one candidate image for this scene only if it is sharp, clean, "
                    "high quality, visually appealing, and clearly relevant. Reject images that look blurry, "
                    "low-resolution, heavily compressed, text-heavy, captioned, logo-only, poster-like, "
                    "infographic-like, UI-like, or screenshot-like. If none are good enough, return selected_index=0."
                ),
            },
            {
                "type": "text",
                "text": (
                    f"Video prompt: {state.prompt}\n"
                    f"Style: {state.style}\n"
                    f"Scene {scene.index}: {scene.title}\n"
                    f"Scene goal: {scene.scene_goal}\n"
                    f"Scene visual prompt: {scene.visual_prompt}\n"
                    f"Preferred on-screen text: {scene.on_screen_text}"
                ),
            },
        ]

        for index, candidate in enumerate(candidates, start=1):
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"Candidate {index}\n"
                        f"Dimensions: {candidate.width}x{candidate.height}\n"
                        f"Source URL: {candidate.source_url}"
                    ),
                }
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": candidate.review_data_url},
                }
            )

        messages = [
            SystemMessage(
                content=(
                    "Return a strict evaluation. Use 'accept' only for images good enough for a polished brand video. "
                    "Prefer real photography or clean premium illustration over noisy graphics."
                )
            ),
            HumanMessage(content=content),
        ]

        try:
            llm = azure_chat_openai_gpt_5_1.with_structured_output(SceneImageSelection)
            return await llm.ainvoke(messages)
        except Exception as exc:
            logger.warning(
                f"[VideoGenerationAgent (AssetNode)] Vision review failed "
                f"scene={scene.index} error={exc}"
            )
            return None

    @staticmethod
    def _is_accepted_assessment(assessment: CandidateAssessment) -> bool:
        return (
            assessment.verdict.strip().lower() == "accept"
            and assessment.quality_score >= 70
            and assessment.relevance_score >= 65
            and not assessment.has_visible_text
            and not assessment.is_blurry
            and not assessment.is_graphic_or_screenshot
        )

    async def _mirror_candidate_to_blob(
        self,
        candidate: CandidateImage,
        user_id: int,
        job_id: int,
    ) -> str | None:
        try:
            extension = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }[candidate.content_type]
            blob_path = (
                f"video-generations/{user_id}/{job_id}/assets/"
                f"{uuid.uuid4().hex}.{extension}"
            )
            blob_storage_client.upload_bytes(
                blob_path=blob_path,
                data=io.BytesIO(candidate.image_bytes),
                content_type=candidate.content_type,
            )
            return blob_storage_client.generate_sas_url(blob_path, expiry_hours=24)
        except Exception as exc:
            logger.debug(
                f"[VideoGenerationAgent (AssetNode)] Unable to mirror candidate image "
                f"url={candidate.source_url} error={exc}"
            )
            return None

    async def _curate_scene_image(
        self,
        state: VideoGenerationAgentState,
        scene: VideoScene,
        source_pool: list[str],
        used_urls: set[str],
        download_cache: dict[str, CandidateImage | None],
    ) -> tuple[str | None, str | None]:
        scene_urls = await self._search_scene_images(state, scene)
        preferred_urls = [url for url in scene_urls if url not in used_urls]
        fallback_urls = [url for url in source_pool if url not in used_urls]
        reused_urls = [url for url in self._dedupe_urls(scene_urls + source_pool) if url in used_urls]
        candidate_urls = self._dedupe_urls(preferred_urls + fallback_urls + reused_urls)

        candidates: list[CandidateImage] = []
        for url in candidate_urls:
            candidate = await self._download_candidate(url, download_cache)
            if candidate is None:
                continue
            candidates.append(candidate)
            if len(candidates) >= MAX_CANDIDATES_PER_SCENE:
                break

        if not candidates:
            return None, None

        review = await self._review_scene_candidates(state, scene, candidates)
        if review is None or review.selected_index <= 0:
            logger.info(
                f"[VideoGenerationAgent (AssetNode)] No approved image for scene={scene.index} "
                f"reason={(review.overall_reason if review else 'vision review unavailable')}"
            )
            return None, None

        if review.selected_index > len(candidates):
            logger.warning(
                f"[VideoGenerationAgent (AssetNode)] Invalid selected_index={review.selected_index} "
                f"scene={scene.index} candidates={len(candidates)}"
            )
            return None, None

        selected_assessment = next(
            (item for item in review.assessments if item.index == review.selected_index),
            None,
        )
        if selected_assessment and not self._is_accepted_assessment(selected_assessment):
            logger.info(
                f"[VideoGenerationAgent (AssetNode)] Rejected selected candidate after policy check "
                f"scene={scene.index} reason={selected_assessment.reason}"
            )
            return None, None

        selected_candidate = candidates[review.selected_index - 1]
        mirrored_url = await self._mirror_candidate_to_blob(
            selected_candidate,
            state.user_id,
            state.job_id,
        )
        if not mirrored_url:
            return None, None

        logger.info(
            f"[VideoGenerationAgent (AssetNode)] Curated image accepted scene={scene.index} "
            f"url={selected_candidate.source_url} reason={review.overall_reason}"
        )
        return mirrored_url, selected_candidate.source_url

    async def _prepare_storyboard_images(
        self,
        state: VideoGenerationAgentState,
    ) -> tuple[list[VideoScene], list[dict]]:
        source_pool = self._collect_source_images(state)
        used_urls: set[str] = set()
        download_cache: dict[str, CandidateImage | None] = {}
        scenes: list[VideoScene] = []
        asset_references: list[dict] = []

        for scene in state.storyboard:
            image_url, source_url = await self._curate_scene_image(
                state=state,
                scene=scene,
                source_pool=source_pool,
                used_urls=used_urls,
                download_cache=download_cache,
            )
            if source_url:
                used_urls.add(source_url)
            if image_url:
                asset_references.append(
                    {
                        "scene_index": scene.index,
                        "scene_title": scene.title,
                        "image_url": image_url,
                        "source_url": source_url,
                        "usage_guidance": (
                            "Use this approved internet image as scene visual material. "
                            "Crop with objectFit cover, apply subtle Ken Burns movement, "
                            "and keep text overlays separate from the image."
                        ),
                    }
                )
            scenes.append(scene.model_copy(update={"image_url": image_url}))

        return scenes, asset_references

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "assets",
                "message": "Curating scene images with quality review...",
            },
        )

        scenes, asset_references = await self._prepare_storyboard_images(state)
        selected_count = sum(1 for scene in scenes if scene.image_url)

        await adispatch_custom_event(
            "status",
            {
                "step": "assets",
                "message": f"Approved {selected_count}/{len(scenes)} visual asset(s).",
            },
        )

        return {
            "storyboard": scenes,
            "creative_direction": {
                **state.creative_direction,
                "asset_references": asset_references,
                "available_tools": [
                    {
                        "name": "video_image_search",
                        "description": (
                            "Search internet images, review with vision LLM, mirror approved "
                            "assets to blob storage, and attach scene.image_url."
                        ),
                    }
                ],
            },
        }
