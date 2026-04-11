from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.image_generation import IMAGE_GENERATION_PROMPTS


service_logger = logger.bind(service="image-prompt-enhance")


class EnhancedPrompt(BaseModel):
    enhanced_prompt: str = Field(description="enhanced English prompt for image generation (max 400 chars)")
    style_category: str = Field(
        default="photorealistic",
        description="detected style: photorealistic, digital_art, anime, oil_painting, concept_art, watercolor, 3d_render, minimalist, vintage, fantasy, pixel_art, sketch"
    )
    style_notes: list[str] = Field(default_factory=list, description="style-specific notes")
    negative_prompt: str = Field(
        default="",
        description="what to avoid in the generated image"
    )


class PromptEnhanceNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: ImageGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: ImageGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "image_prompt_enhance",
                "message": "🎨 Enhancing image prompt for professional quality...",
            },
        )

        # Build conversation context from memories
        context = ""
        if state.memories:
            recent_messages = state.memories[-3:] if len(state.memories) > 3 else state.memories
            context = "\n".join([
                f"{'User' if getattr(msg, 'role', '') == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:150]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=IMAGE_GENERATION_PROMPTS["PROMPT_ENHANCE_SYSTEM"]),
            HumanMessage(content=IMAGE_GENERATION_PROMPTS["PROMPT_ENHANCE_USER"].format(
                user_question=state.user_question,
                context=context[:500] if context else "No previous context",
            )),
        ]

        service_logger.info(f"Enhancing prompt: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(EnhancedPrompt)
        result = await llm_with_structure.ainvoke(messages)

        # Ensure prompt doesn't exceed 400 chars (DALL-E limit)
        enhanced = result.enhanced_prompt
        if len(enhanced) > 400:
            enhanced = enhanced[:397] + "..."
            service_logger.info(f"Truncated enhanced prompt from {len(result.enhanced_prompt)} to 400 chars")

        service_logger.info(
            f"Enhanced prompt: '{enhanced[:100]}...' | "
            f"Style: {result.style_category} | "
            f"Negative: '{result.negative_prompt[:60]}...'"
        )

        dispatch_custom_event(
            "status",
            {
                "step": "image_prompt_enhance",
                "message": f"✨ Prompt enhanced (style: {result.style_category})",
            },
        )

        return {
            "enhanced_prompt": enhanced,
        }