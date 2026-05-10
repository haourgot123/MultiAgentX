import math
import re
from typing import List

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from loguru import logger
from pydantic import BaseModel, Field

from backend.agents.video_generation_agent.state import (
    VideoGenerationAgentState,
    VideoScene,
)
from backend.utils.llm import azure_chat_openai_gpt_5_1



class StoryboardSceneDraft(BaseModel):
    title: str = Field(description="Short scene title")
    scene_goal: str = Field(description="What this scene achieves in the story")
    narration: str = Field(description="Narration script for this scene")
    visual_prompt: str = Field(description="Specific visual direction for this scene")
    on_screen_text: str = Field(description="Short text overlay, max 12 words")
    camera_motion: str = Field(description="Camera or motion feel for the scene")
    visual_motif: str = Field(description="Memorable object, shape, or motif in frame")
    layout_hint: str = Field(
        description=(
            "One of: split-left, split-right, center-stage, editorial-stack, "
            "full-bleed, frame-inset, diagonal-feature, mosaic-cards"
        )
    )
    composition_notes: str = Field(description="Specific framing and composition notes")
    headline_treatment: str = Field(
        description="One of: kinetic-words, poster-stack, ribbon-highlight, minimal-fade"
    )
    transition_to_next: str = Field(description="How the scene should flow into the next")
    duration_seconds: int = Field(description="Scene duration in seconds")


class StoryboardDraft(BaseModel):
    scenes: List[StoryboardSceneDraft] = Field(description="Ordered video scenes")


class StoryboardNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    @staticmethod
    def _fallback_storyboard(state: VideoGenerationAgentState) -> list[VideoScene]:
        scene_count = min(5, max(3, math.ceil(state.duration_seconds / 6)))
        base_duration = state.duration_seconds // scene_count
        remainder = state.duration_seconds % scene_count
        scene_blueprints = [
            {
                "title": "Opening Hook",
                "scene_goal": "Hook the audience immediately with the core promise.",
                "narration": f"Open with a sharp, engaging setup around {state.prompt}.",
                "on_screen_text": "Nhanh hon. On dinh hon.",
                "camera_motion": "push-in with subtle parallax drift",
                "visual_motif": "hero glow and directional light streaks",
                "transition_to_next": "accelerate into the next product beat",
            },
            {
                "title": "Problem Setup",
                "scene_goal": "Show the friction that the product solves in daily use.",
                "narration": f"Reveal the pain point behind {state.prompt} in a relatable moment.",
                "on_screen_text": "Ket noi muot ma moi luc",
                "camera_motion": "gentle lateral drift with layered depth",
                "visual_motif": "contrast between signal stress and calm clarity",
                "transition_to_next": "shift from tension to solution reveal",
            },
            {
                "title": "Solution Reveal",
                "scene_goal": "Introduce the product as the clean and credible answer.",
                "narration": f"Position {state.prompt} as the confident step up for the audience.",
                "on_screen_text": "WiFi 6 cho moi nha",
                "camera_motion": "rise reveal with light sweep",
                "visual_motif": "centered product hero with luminous accents",
                "transition_to_next": "expand into concrete product benefits",
            },
            {
                "title": "Key Benefits",
                "scene_goal": "Translate features into tangible user benefits.",
                "narration": f"Break down the strongest benefit of {state.prompt} in a clear visual beat.",
                "on_screen_text": "Toc do va do on dinh",
                "camera_motion": "editorial pan with kinetic overlays",
                "visual_motif": "structured comparison shapes and premium data cues",
                "transition_to_next": "pivot into offer or package detail",
            },
            {
                "title": "Offer Close",
                "scene_goal": "Land the offer with a persuasive closing beat.",
                "narration": f"Close with a memorable invitation to choose {state.prompt}.",
                "on_screen_text": "Nang cap ngay hom nay",
                "camera_motion": "slow settle-in with final highlight bloom",
                "visual_motif": "clean CTA plate and confident brand finish",
                "transition_to_next": "hold on the final brand impression",
            },
        ]

        scenes: list[VideoScene] = []
        for index in range(scene_count):
            duration = base_duration + (1 if index < remainder else 0)
            blueprint = scene_blueprints[index % len(scene_blueprints)]
            scenes.append(
                VideoScene(
                    index=index + 1,
                    title=blueprint["title"],
                    scene_goal=blueprint["scene_goal"],
                    narration=blueprint["narration"],
                    visual_prompt=(
                        f"{state.style} visual scene about {state.prompt}, "
                        "clean composition, modern lighting, layered depth"
                    ),
                    on_screen_text=blueprint["on_screen_text"],
                    camera_motion=blueprint["camera_motion"],
                    visual_motif=blueprint["visual_motif"],
                    layout_hint=[
                        "split-left",
                        "split-right",
                        "center-stage",
                        "full-bleed",
                        "frame-inset",
                    ][index % 5],
                    composition_notes="Create strong depth separation with one dominant focal plane.",
                    headline_treatment=[
                        "kinetic-words",
                        "poster-stack",
                        "ribbon-highlight",
                        "minimal-fade",
                    ][index % 4],
                    transition_to_next=blueprint["transition_to_next"],
                    duration_seconds=max(duration, 2),
                )
            )
        return self_trim_scenes(scenes, state.duration_seconds)

    @staticmethod
    def _is_content_filter_error(exc: Exception) -> bool:
        error_text = repr(exc).lower()
        return "content_filter" in error_text or "responsibleaipolicyviolation" in error_text

    @staticmethod
    def _clean_context_text(value: str, max_chars: int) -> str:
        cleaned = re.sub(r"https?://\S+", "", value or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:max_chars]

    @classmethod
    def _build_source_context(
        cls,
        state: VideoGenerationAgentState,
        *,
        include_sources: bool,
    ) -> str:
        if not include_sources:
            return "No external sources."

        lines: list[str] = []
        for source in state.sources[:4]:
            title = cls._clean_context_text(source.title, 80)
            snippet = cls._clean_context_text(source.snippet, 180)
            if title and snippet:
                lines.append(f"- {title}: {snippet}")
            elif title:
                lines.append(f"- {title}")
            elif snippet:
                lines.append(f"- {snippet}")
        return "\n".join(lines) or "No external sources."

    @classmethod
    def _build_messages(
        cls,
        state: VideoGenerationAgentState,
        *,
        include_sources: bool,
        compact_mode: bool,
    ) -> list[SystemMessage | HumanMessage]:
        source_context = cls._build_source_context(state, include_sources=include_sources)
        skill_context = cls._clean_context_text(
            state.skill_bundle.get("summary", "No skill guidance loaded."),
            1200 if not compact_mode else 500,
        )

        compact_tail = (
            "Keep the language neutral, brand-safe, and practical. Avoid edgy phrasing. "
            if compact_mode
            else ""
        )

        return [
            SystemMessage(
                content=(
                    "You create scene-by-scene storyboard JSON for short Remotion videos. "
                    "Do not write code. Make the sequence feel like one continuous professional film: "
                    "start with a hook, build visual escalation, then land a payoff. "
                    "Each scene must have a distinct role, memorable motif, layout hint, composition note, "
                    "headline treatment, and transition. "
                    f"{compact_tail}"
                    "Respect the following Remotion skill guidance while planning scenes:\n"
                    f"{skill_context}"
                )
            ),
            HumanMessage(
                content=(
                    f"Prompt: {cls._clean_context_text(state.prompt, 220)}\n"
                    f"Style: {state.style}\n"
                    f"Duration: {state.duration_seconds}s\n"
                    f"Aspect ratio: {state.aspect_ratio}\n"
                    f"Sources:\n{source_context}\n\n"
                    "Create 3-8 scenes. Each scene duration must be 2-8 seconds. "
                    "Keep on-screen text short. Keep narration tightly connected from one scene to the next. "
                    "Do not keep repeating the same left-right composition. Use at least 3 distinct layout hints "
                    "across the video when scene count allows. "
                    "Use layout hints from this set only: split-left, split-right, center-stage, editorial-stack, "
                    "full-bleed, frame-inset, diagonal-feature, mosaic-cards. "
                    "Use headline treatments from this set only: kinetic-words, poster-stack, ribbon-highlight, minimal-fade."
                )
            ),
        ]

    @staticmethod
    def _normalize_scenes(
        state: VideoGenerationAgentState,
        draft_scenes: list[StoryboardSceneDraft],
    ) -> list[VideoScene]:
        scenes: list[VideoScene] = []
        total = 0
        for index, draft in enumerate(draft_scenes[:8], 1):
            remaining = state.duration_seconds - total
            if remaining <= 0:
                break
            duration = min(max(int(draft.duration_seconds or 3), 2), 8, remaining)
            scenes.append(
                VideoScene(
                    index=index,
                    title=draft.title.strip()[:80] or f"Scene {index}",
                    scene_goal=draft.scene_goal.strip(),
                    narration=draft.narration.strip(),
                    visual_prompt=draft.visual_prompt.strip(),
                    on_screen_text=draft.on_screen_text.strip()[:100],
                    camera_motion=draft.camera_motion.strip()[:120],
                    visual_motif=draft.visual_motif.strip()[:120],
                    layout_hint=draft.layout_hint.strip()[:40],
                    composition_notes=draft.composition_notes.strip()[:180],
                    headline_treatment=draft.headline_treatment.strip()[:40],
                    transition_to_next=draft.transition_to_next.strip()[:120],
                    duration_seconds=duration,
                )
            )
            total += duration

        if not scenes:
            return StoryboardNode._fallback_storyboard(state)

        if total < state.duration_seconds:
            scenes[-1].duration_seconds += state.duration_seconds - total

        return self_trim_scenes(scenes, state.duration_seconds)

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "storyboard",
                "message": "Creating storyboard...",
            },
        )

        try:
            llm = azure_chat_openai_gpt_5_1.with_structured_output(StoryboardDraft)
            try:
                draft = await llm.ainvoke(
                    self._build_messages(
                        state,
                        include_sources=True,
                        compact_mode=False,
                    )
                )
            except Exception as exc:
                if not self._is_content_filter_error(exc):
                    raise

                logger.warning(
                    "[VideoGenerationAgent (StoryboardNode)] Content filter triggered on storyboard prompt; "
                    "retrying with sanitized context."
                )
                draft = await llm.ainvoke(
                    self._build_messages(
                        state,
                        include_sources=False,
                        compact_mode=True,
                    )
                )

            scenes = self._normalize_scenes(state, draft.scenes)
        except Exception as exc:
            logger.warning(f"[VideoGenerationAgent (StoryboardNode)] LLM storyboard failed, using fallback: {exc}")
            scenes = self._fallback_storyboard(state)

        storyboard_payload = [scene.model_dump() for scene in scenes]
        await adispatch_custom_event("storyboard", {"scenes": storyboard_payload})
        return {"storyboard": scenes}


def self_trim_scenes(scenes: list[VideoScene], max_duration: int) -> list[VideoScene]:
    total = 0
    trimmed: list[VideoScene] = []
    for index, scene in enumerate(scenes, 1):
        remaining = max_duration - total
        if remaining <= 0:
            break
        duration = min(scene.duration_seconds, remaining)
        trimmed.append(scene.model_copy(update={"index": index, "duration_seconds": duration}))
        total += duration
    return trimmed
