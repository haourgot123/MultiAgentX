from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="image-prompt-enhance")


class EnhancedPrompt(BaseModel):
    enhanced_prompt: str = Field(description="enhanced prompt for image generation")
    style_notes: list[str] = Field(default_factory=list, description="style notes to consider")


PROMPT_ENHANCE_SYSTEM = """You are an expert prompt engineer for AI image generation models.
Your task is to enhance user prompts to create more detailed, vivid, and artistic image descriptions.

Guidelines for enhancement:
1. Add visual details (colors, textures, lighting, composition)
2. Include artistic style references (realistic, abstract, impressionistic, etc.)
3. Specify perspective and framing (close-up, wide shot, bird's eye view)
4. Add mood and atmosphere descriptors
5. Include technical quality terms (high resolution, detailed, sharp focus)
6. Keep the core subject and intent intact
7. Make the prompt descriptive but concise (under 400characters)

Respond in the same language as the user's request.

Example:
User: "mèo ngồi cửa sổ"
Enhanced: "A fluffy cat sitting gracefully on a sunlit windowsill, soft golden hour lighting streaming through sheer curtains, detailed fur texture with subtle shadows, cozy indoor atmosphere, photorealistic style, high detail, 4K quality"

User: "sunset over mountains"
Enhanced: "Breathtaking sunset over majestic mountain peaks, vibrant orange and purple sky with scattered clouds, silhouetted pine trees in foreground, dramatic atmospheric perspective, golden hour glow, photorealistic landscape photography, ultra high resolution""" 


PROMPT_ENHANCE_USER = """Enhance this image generation prompt for better visual quality:

User Request: {user_question}

Conversation Context: {context}

Create an enhanced prompt that will produce a stunning image."""


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
                "message": "🎨 Enhancing image prompt for better quality...",
            },
        )

        context = ""
        if state.memories:
            recent_messages = state.memories[-3:] if len(state.memories) > 3 else state.memories
            context = "\n".join([
                f"{'User' if getattr(msg, 'role', '') == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:150]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=PROMPT_ENHANCE_SYSTEM),
            HumanMessage(content=PROMPT_ENHANCE_USER.format(
                user_question=state.user_question,
                context=context[:500] if context else "No previous context",
            )),
        ]

        service_logger.info(f"Enhancing prompt: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(EnhancedPrompt)
        result = await llm_with_structure.ainvoke(messages)

        service_logger.info(f"Enhanced prompt: '{result.enhanced_prompt[:100]}...'")

        dispatch_custom_event(
            "status",
            {
                "step": "image_prompt_enhance",
                "message": f"✅ Enhanced prompt ready.",
            },
        )

        return {
            "enhanced_prompt": result.enhanced_prompt,
        }