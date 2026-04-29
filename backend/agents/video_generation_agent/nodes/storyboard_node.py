import math
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
    narration: str = Field(description="Narration script for this scene")
    visual_prompt: str = Field(description="Specific visual direction for this scene")
    on_screen_text: str = Field(description="Short text overlay, max 12 words")
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

        scenes: list[VideoScene] = []
        for index in range(scene_count):
            duration = base_duration + (1 if index < remainder else 0)
            scenes.append(
                VideoScene(
                    index=index + 1,
                    title=f"Scene {index + 1}",
                    narration=(
                        f"Introduce and develop the idea: {state.prompt}"
                        if index == 0
                        else f"Continue the story with a clear visual beat about {state.prompt}."
                    ),
                    visual_prompt=(
                        f"{state.style} visual scene about {state.prompt}, "
                        "clean composition, modern lighting"
                    ),
                    on_screen_text=state.prompt[:72],
                    duration_seconds=max(duration, 2),
                )
            )
        return self_trim_scenes(scenes, state.duration_seconds)

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
                    narration=draft.narration.strip(),
                    visual_prompt=draft.visual_prompt.strip(),
                    on_screen_text=draft.on_screen_text.strip()[:100],
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

        source_context = "\n".join(
            f"- {source.title}: {source.snippet} ({source.url})"
            for source in state.sources[:4]
        )
        source_context = source_context or "No external sources."

        messages = [
            SystemMessage(
                content=(
                    "You create concise storyboard JSON for short Remotion videos. "
                    "Do not write code. Keep scenes visual, factual when sources are provided, "
                    "and make total duration fit the requested length."
                )
            ),
            HumanMessage(
                content=(
                    f"Prompt: {state.prompt}\n"
                    f"Style: {state.style}\n"
                    f"Duration: {state.duration_seconds}s\n"
                    f"Aspect ratio: {state.aspect_ratio}\n"
                    f"Sources:\n{source_context}\n\n"
                    "Create 3-8 scenes. Each scene duration must be 2-8 seconds. "
                    "Keep on-screen text short."
                )
            ),
        ]

        try:
            llm = azure_chat_openai_gpt_5_1.with_structured_output(StoryboardDraft)
            draft = await llm.ainvoke(messages)
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
