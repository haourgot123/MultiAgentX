import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai.chat_models import AzureChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

from backend.config.settings import _settings


class RemotionCodeDraft(BaseModel):
    rationale: str = Field(description="Brief implementation rationale")
    code: str = Field(description="Complete TypeScript TSX source for video_renderer entry index.tsx")


def _strip_code_fence(code: str) -> str:
    cleaned = (code or "").strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _validate_generated_remotion_code(code: str, composition_id: str) -> None:
    required_tokens = [
        "registerRoot",
        "Composition",
        "AbsoluteFill",
        "useCurrentFrame",
        "interpolate",
        composition_id,
    ]
    missing = [token for token in required_tokens if token not in code]
    if missing:
        raise ValueError(f"Generated Remotion code is missing required token(s): {', '.join(missing)}")

    forbidden_tokens = [
        "transition:",
        "animation:",
        "@keyframes",
        "setInterval(",
        "setTimeout(",
        "document.",
        "window.",
    ]
    forbidden = [token for token in forbidden_tokens if token in code]
    if forbidden:
        raise ValueError(f"Generated Remotion code contains forbidden token(s): {', '.join(forbidden)}")


def _compact_json(value: Any, max_chars: int = 14000) -> str:
    serialized = json.dumps(value, ensure_ascii=False, indent=2)
    if len(serialized) <= max_chars:
        return serialized
    return serialized[:max_chars].rstrip() + "\n/* truncated for prompt */"


def _clean_text(value: Any, max_chars: int) -> str:
    cleaned = " ".join(str(value or "").replace("\n", " ").split())
    return cleaned[:max_chars]


def _is_content_filter_error(exc: Exception) -> bool:
    error_text = repr(exc).lower()
    return "content_filter" in error_text or "responsibleaipolicyviolation" in error_text


def _scene_codegen_payload(scene: dict[str, Any], *, compact_mode: bool) -> dict[str, Any]:
    payload = {
        "index": scene.get("index"),
        "title": _clean_text(scene.get("title"), 48),
        "headline": _clean_text(scene.get("on_screen_text") or scene.get("title"), 54),
        "layout_hint": _clean_text(scene.get("layout_hint"), 32),
        "headline_treatment": _clean_text(scene.get("headline_treatment"), 32),
        "duration_seconds": scene.get("duration_seconds"),
        "image_url": scene.get("image_url"),
    }
    if compact_mode:
        return payload

    payload.update(
        {
            "narration": _clean_text(scene.get("narration"), 150),
            "scene_goal": _clean_text(scene.get("scene_goal"), 90),
        }
    )
    return payload


def _codegen_payload(
    remotion_input: dict[str, Any],
    creative_direction: dict[str, Any],
    *,
    compact_mode: bool = False,
) -> dict[str, Any]:
    scene_directions = creative_direction.get("scene_directions") or []
    payload = {
        "jobId": remotion_input.get("jobId"),
        "prompt": _clean_text(
            remotion_input.get("prompt"),
            84 if compact_mode else 180,
        ),
        "style": remotion_input.get("style"),
        "durationSeconds": remotion_input.get("durationSeconds"),
        "fps": remotion_input.get("fps"),
        "width": remotion_input.get("width"),
        "height": remotion_input.get("height"),
        "aspectRatio": remotion_input.get("aspectRatio"),
        "compositionId": remotion_input.get("compositionId"),
        "scenes": [
            _scene_codegen_payload(scene, compact_mode=compact_mode)
            for scene in (remotion_input.get("scenes") or [])[:8]
        ],
        "creativeDirection": {
            "concept": _clean_text(
                creative_direction.get("concept"),
                72 if compact_mode else 140,
            ),
            "visual_archetype": creative_direction.get("visual_archetype"),
            "layout_recipe": _clean_text(
                creative_direction.get("layout_recipe"),
                80 if compact_mode else 140,
            ),
            "background_treatment": _clean_text(
                creative_direction.get("background_treatment"),
                80 if compact_mode else 140,
            ),
            "motion_principle": _clean_text(
                creative_direction.get("motion_principle"),
                80 if compact_mode else 140,
            ),
            "typography_tone": _clean_text(
                creative_direction.get("typography_tone"),
                60 if compact_mode else 100,
            ),
            "font_profile": creative_direction.get("font_profile"),
            "color_palette": (creative_direction.get("color_palette") or [])[:5],
            "accent_words": [
                _clean_text(item, 18 if compact_mode else 24)
                for item in (creative_direction.get("accent_words") or [])[:4]
            ],
            "scene_directions": [
                {
                    "scene_index": item.get("scene_index"),
                    "emphasis": _clean_text(
                        item.get("emphasis"),
                        40 if compact_mode else 80,
                    ),
                    "layout_variant": item.get("layout_variant"),
                    "headline_treatment": item.get("headline_treatment"),
                    "font_profile": item.get("font_profile"),
                    "entrance_motion": _clean_text(
                        item.get("entrance_motion"),
                        32 if compact_mode else 60,
                    ),
                    "background_motion": _clean_text(
                        item.get("background_motion"),
                        32 if compact_mode else 60,
                    ),
                    "transition_hint": _clean_text(
                        item.get("transition_hint"),
                        32 if compact_mode else 60,
                    ),
                }
                for item in scene_directions[:8]
            ],
        },
    }
    if compact_mode:
        return payload

    payload["assetReferences"] = [
            {
                "scene_index": item.get("scene_index"),
                "image_url": item.get("image_url"),
                "usage_guidance": _clean_text(item.get("usage_guidance"), 120),
            }
            for item in (remotion_input.get("assetReferences") or [])[:8]
        ]
    return payload


def _skill_codegen_summary(
    skill_bundle: dict[str, Any],
    *,
    compact_mode: bool = False,
) -> str:
    rules = skill_bundle.get("rules") or {}
    selected = [
        "Use Remotion frame-driven animation with useCurrentFrame(), useVideoConfig(), interpolate(), and Easing.",
        "Use Sequence for timing and scene orchestration.",
        "Use <Img> for remote image URLs and animate transforms frame-by-frame.",
        "Do not use CSS transitions, CSS animations, keyframes, timers, DOM APIs, or browser globals.",
        "Keep component props runtime-configurable and register a Composition in the root.",
    ]
    if compact_mode:
        return "\n".join(f"- {item}" for item in selected)

    for name in ("sequencing", "timing", "images", "text-animations"):
        content = rules.get(name)
        if content:
            selected.append(_clean_text(content, 500))
    return "\n".join(f"- {item}" for item in selected)


def _repair_error_summary(exc: Exception) -> str:
    if _is_content_filter_error(exc):
        return "The previous attempt returned no usable code. Retry with the minimal payload."
    return repr(exc)[:1200]


def _codegen_llm():
    config = _settings.azure_chat_openai
    return AzureChatOpenAI(
        api_key=config.api_key,
        api_version=config.api_version,
        azure_endpoint=config.api_endpoint,
        azure_deployment=config.deployment_name_gpt_5_1,
        temperature=0,
        top_p=1.0,
        n=1,
        disable_streaming=True,
        max_retries=1,
        verbosity="low",
    )


def _build_codegen_messages(
    *,
    remotion_input: dict[str, Any],
    creative_direction: dict[str, Any],
    composition_id: str,
    skill_bundle: dict[str, Any],
    compact_mode: bool = False,
) -> list[SystemMessage | HumanMessage]:
    skill_summary = _skill_codegen_summary(skill_bundle, compact_mode=compact_mode)
    composition_id_json = json.dumps(composition_id, ensure_ascii=False)
    payload = _codegen_payload(
        remotion_input,
        creative_direction,
        compact_mode=compact_mode,
    )
    payload_label = (
        "Minimal sanitized codegen payload JSON"
        if compact_mode
        else "Sanitized codegen payload JSON"
    )
    return [
        SystemMessage(
            content=(
                "You are a senior Remotion engineer. Generate a complete, production-ready "
                "video_renderer entry file in TSX. You are not filling a fixed template; design the "
                "composition structure, helper components, layouts, typography, palette, and motion system "
                "from the supplied storyboard and creative direction.\n\n"
                "Hard requirements:\n"
                "- Return only structured output with a complete `code` string.\n"
                "- The code must import from `remotion` and call `registerRoot(RemotionRoot)`.\n"
                f"- The root must register a Composition with id {composition_id_json}.\n"
                "- The composition must accept the supplied VideoInput props and also include embedded default props.\n"
                "- Use Remotion frame-driven animation only: `useCurrentFrame`, `useVideoConfig`, `interpolate`, `Easing`, `Sequence`.\n"
                "- Do not use CSS transitions, CSS animations, `@keyframes`, timers, DOM APIs, or browser globals.\n"
                "- Text must fit inside its visual region in 16:9, 9:16, and 1:1. Truncate, wrap, or reduce density explicitly.\n"
                "- Do not render internal planning notes such as composition_notes, camera_motion, or visual_prompt as visible UI text.\n"
                "- Do not render scene counters like 01/05 or large background scene numbers.\n"
                "- Do not create boxed word tiles, vertical stacks of isolated words, long pill headers, or fake progress bars.\n"
                "- Use readable line-based typography: short headline, optional subhead, concise body. Keep letter spacing at 0 or positive.\n"
                "- Use cohesive colors derived from the creative direction, not a one-note blue/purple slab.\n"
                "- Prefer varied scene layouts and code-drawn visual elements where stock imagery is weak or unavailable.\n\n"
                "Tool usage context:\n"
                "- A `video_image_search` tool may have already searched the internet, reviewed images with vision LLM, "
                "mirrored approved images to blob storage, and attached them as `scene.image_url` plus "
                "`remotion_input.assetReferences`.\n"
                "- When approved image URLs are present, use them as visual material with Remotion `<Img>`: "
                "cover crop, subtle Ken Burns movement, tasteful overlays, and no visible source/caption text.\n"
                "- When a scene has no approved image, create lively code-drawn visual elements instead of leaving a dead layout.\n\n"
                "Apply this loaded skill guidance using progressive disclosure:\n"
                f"{skill_summary}"
            )
        ),
        HumanMessage(
            content=(
                "Generate the complete TSX source for `video_renderer/.generated/<job_id>/index.tsx`.\n\n"
                f"{payload_label}:\n"
                f"{_compact_json(payload, max_chars=9000)}\n\n"
                "Implementation notes:\n"
                "- The code can define helper functions/components freely.\n"
                "- Use `calculateMetadata` or robust defaults so runtime input props can control width, height, fps, and duration.\n"
                "- Keep the generated file self-contained. Do not import local project files."
            )
        ),
    ]


def _build_codegen_repair_messages(
    *,
    remotion_input: dict[str, Any],
    creative_direction: dict[str, Any],
    composition_id: str,
    skill_bundle: dict[str, Any],
    previous_error: str,
    compact_mode: bool = False,
) -> list[SystemMessage | HumanMessage]:
    messages = _build_codegen_messages(
        remotion_input=remotion_input,
        creative_direction=creative_direction,
        composition_id=composition_id,
        skill_bundle=skill_bundle,
        compact_mode=compact_mode,
    )
    messages.append(
        HumanMessage(
            content=(
                "The previous generated TSX returned no usable render source.\n"
                f"Validation error: {previous_error[:1200]}\n\n"
                "Regenerate the complete TSX source from scratch. Keep the design materially different "
                "from any fixed template: no boxed word stacks, no scene counters, no progress bars, "
                "no long pill labels, and no one-color blue interface. "
                "Stay brand-safe and avoid echoing any unsafe or sensitive wording from the request."
            )
        )
    )
    return messages


async def generate_remotion_entry_with_llm(
    *,
    remotion_input: dict[str, Any],
    creative_direction: dict[str, Any],
    composition_id: str,
    skill_bundle: dict[str, Any],
) -> str:
    llm = _codegen_llm().with_structured_output(RemotionCodeDraft)
    messages = _build_codegen_messages(
        remotion_input=remotion_input,
        creative_direction=creative_direction,
        composition_id=composition_id,
        skill_bundle=skill_bundle,
        compact_mode=True,
    )
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            draft = await llm.ainvoke(messages)
            code = _strip_code_fence(draft.code)
            _validate_generated_remotion_code(code, composition_id)
            logger.info(
                "[VideoGenerationAgent (CodeGenerationNode)] Generated Remotion source with LLM: {} chars attempt={}",
                len(code),
                attempt + 1,
            )
            return code
        except Exception as exc:
            last_error = exc
            if attempt == 1:
                break
            logger.opt(exception=exc).warning(
                "[VideoGenerationAgent (CodeGenerationNode)] LLM Remotion codegen attempt failed; retrying with repair prompt."
            )
            messages = _build_codegen_repair_messages(
                remotion_input=remotion_input,
                creative_direction=creative_direction,
                composition_id=composition_id,
                skill_bundle=skill_bundle,
                previous_error=_repair_error_summary(exc),
                compact_mode=True,
            )

    raise RuntimeError("LLM Remotion code generation failed after repair attempt") from last_error


async def generate_remotion_entry(
    *,
    remotion_input: dict[str, Any],
    creative_direction: dict[str, Any],
    composition_id: str,
    skill_bundle: dict[str, Any],
) -> str:
    return await generate_remotion_entry_with_llm(
        remotion_input=remotion_input,
        creative_direction=creative_direction,
        composition_id=composition_id,
        skill_bundle=skill_bundle,
    )
