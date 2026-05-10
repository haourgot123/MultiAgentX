from typing import List

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from loguru import logger
from pydantic import BaseModel, Field

from backend.agents.video_generation_agent.state import VideoGenerationAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


STYLE_PALETTES = {
    "cinematic": ["#06131f", "#214e80", "#d2a35c", "#f3ebdc"],
    "educational": ["#0b1728", "#2f7ae5", "#5fd3ff", "#eef6ff"],
    "product_demo": ["#111827", "#2563eb", "#14b8a6", "#f8fafc"],
    "social_short": ["#140f2d", "#f43f5e", "#fb7185", "#fff1f2"],
    "slideshow": ["#0f172a", "#475569", "#38bdf8", "#e2e8f0"],
}


class SceneDirectionDraft(BaseModel):
    scene_index: int = Field(description="Scene index")
    emphasis: str = Field(description="Primary storytelling emphasis for the scene")
    layout_variant: str = Field(
        description=(
            "One of: split-left, split-right, center-stage, editorial-stack, "
            "full-bleed, frame-inset, diagonal-feature, mosaic-cards"
        )
    )
    headline_treatment: str = Field(
        description="One of: kinetic-words, poster-stack, ribbon-highlight, minimal-fade"
    )
    font_profile: str = Field(
        description="One of: cinematic-serif, magazine-condensed, neo-grotesk, humanist-clean"
    )
    entrance_motion: str = Field(description="Short description of entrance motion")
    background_motion: str = Field(description="Short description of background motion")
    transition_hint: str = Field(description="How the scene should hand off to the next")


class CreativeDirectionDraft(BaseModel):
    concept: str = Field(description="One sentence creative thesis")
    visual_archetype: str = Field(
        description=(
            "One of: luxury-editorial, tech-keynote, social-kinetic, "
            "documentary-explainer, product-launch, cinematic-minimal"
        )
    )
    layout_recipe: str = Field(description="Overall layout system for the full video")
    background_treatment: str = Field(description="Background art direction")
    motion_principle: str = Field(description="Consistent motion principle")
    typography_tone: str = Field(description="Typography direction")
    font_profile: str = Field(
        description="One of: cinematic-serif, magazine-condensed, neo-grotesk, humanist-clean"
    )
    color_palette: List[str] = Field(description="3-5 hex colors")
    accent_words: List[str] = Field(description="1-4 short anchor words")
    scene_directions: List[SceneDirectionDraft] = Field(
        description="Per-scene motion and layout directions"
    )


class CreativeDirectionNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    @staticmethod
    def _fallback_direction(state: VideoGenerationAgentState) -> dict:
        palette = STYLE_PALETTES.get(state.style, STYLE_PALETTES["educational"])
        visual_archetype = {
            "cinematic": "cinematic-minimal",
            "educational": "documentary-explainer",
            "product_demo": "product-launch",
            "social_short": "social-kinetic",
            "slideshow": "luxury-editorial",
        }.get(state.style, "documentary-explainer")
        layout_cycle = [
            "split-left",
            "split-right",
            "center-stage",
            "editorial-stack",
            "full-bleed",
            "frame-inset",
            "diagonal-feature",
            "mosaic-cards",
        ]
        font_profile = {
            "cinematic": "cinematic-serif",
            "educational": "humanist-clean",
            "product_demo": "magazine-condensed",
            "social_short": "neo-grotesk",
            "slideshow": "cinematic-serif",
        }.get(state.style, "humanist-clean")
        treatment_cycle = [
            "kinetic-words",
            "poster-stack",
            "ribbon-highlight",
            "minimal-fade",
        ]
        scene_directions = []
        for index, scene in enumerate(state.storyboard, start=1):
            scene_directions.append(
                {
                    "scene_index": scene.index,
                    "emphasis": scene.scene_goal or "clear progression",
                    "layout_variant": scene.layout_hint or layout_cycle[(index - 1) % len(layout_cycle)],
                    "headline_treatment": scene.headline_treatment or treatment_cycle[(index - 1) % len(treatment_cycle)],
                    "font_profile": font_profile,
                    "entrance_motion": scene.camera_motion or "soft rise with depth",
                    "background_motion": "ambient glow with slow drift",
                    "transition_hint": scene.transition_to_next or "clean dissolve",
                }
            )

        return {
            "concept": f"Scene-driven {state.style} story built around {state.prompt}",
            "visual_archetype": visual_archetype,
            "layout_recipe": "alternating split compositions with one centered payoff scene",
            "background_treatment": "layered gradients with luminous depth and restrained glass panels",
            "motion_principle": "use interpolate with ease-out entrances and ease-in exits",
            "typography_tone": "bold editorial sans with concise overlays",
            "font_profile": font_profile,
            "color_palette": palette,
            "accent_words": ["hook", "build", "payoff"],
            "scene_directions": scene_directions,
        }

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "creative_direction",
                "message": "Designing the visual system and scene choreography...",
            },
        )

        skill_context = state.skill_bundle.get("summary", "No skill guidance loaded.")
        storyboard_context = "\n".join(
            (
                f"- Scene {scene.index}: {scene.title} | goal={scene.scene_goal} | "
                f"layout={scene.layout_hint} | motion={scene.camera_motion} | "
                f"transition={scene.transition_to_next}"
            )
            for scene in state.storyboard
        )
        messages = [
            SystemMessage(
                content=(
                    "You are a senior motion director for Remotion videos. "
                    "Build a creative direction that can later be translated into code. "
                    "Respect this skill guidance and keep the output implementation-friendly:\n"
                    f"{skill_context}"
                )
            ),
            HumanMessage(
                content=(
                    f"Prompt: {state.prompt}\n"
                    f"Style: {state.style}\n"
                    f"Aspect ratio: {state.aspect_ratio}\n"
                    f"Requested duration: {state.duration_seconds}s\n"
                    f"Storyboard:\n{storyboard_context}\n\n"
                    "Return a polished but practical art direction. "
                    "Use alternating layouts so scenes do not feel repetitive. "
                    "Choose one visual archetype from this set only: luxury-editorial, tech-keynote, "
                    "social-kinetic, documentary-explainer, product-launch, cinematic-minimal. "
                    "Choose a font profile that matches the brand tone and do not repeat one layout pattern too often."
                )
            ),
        ]

        try:
            llm = azure_chat_openai_gpt_5_1.with_structured_output(CreativeDirectionDraft)
            draft = await llm.ainvoke(messages)
            direction = draft.model_dump()
            if not direction.get("scene_directions"):
                direction = self._fallback_direction(state)
        except Exception as exc:
            logger.warning(
                f"[VideoGenerationAgent (CreativeDirectionNode)] LLM direction failed, using fallback: {exc}"
            )
            direction = self._fallback_direction(state)

        return {"creative_direction": direction}
