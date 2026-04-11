from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.agents.general_agent.tools.image_generator import image_generation_service


service_logger = logger.bind(service="image-generate")


class GenerateNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: ImageGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: ImageGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "image_generate",
                "message": "Generating image...",
            },
        )

        prompt = state.enhanced_prompt if state.enhanced_prompt else state.user_question

        service_logger.info(f"Generating image for prompt: '{prompt[:100]}...'")

        try:
            result = await image_generation_service.generate_with_retry(
                prompt=prompt,
                max_retries=3,
            )

            if not result.urls:
                service_logger.error("No image URLs returned")
                return {
                    "error_message": "Image generation failed: No images were generated.",
                    "image_urls": [],
                }

            service_logger.info(f"Generated {len(result.urls)} images")

            dispatch_custom_event(
                "status",
                {
                    "step": "image_generate",
                    "message": f"Generated {len(result.urls)} image(s).",
                },
            )

            return {
                "image_urls": result.urls,
                "revised_prompt": result.revised_prompt or "",
                "error_message": "",
            }

        except Exception as e:
            service_logger.error(f"Image generation error: {e}")
            dispatch_custom_event(
                "status",
                {
                    "step": "image_generate",
                    "message": f"Image generation failed: {str(e)[:100]}",
                },
            )
            return {
                "error_message": f"Image generation failed: {str(e)}",
                "image_urls": [],
            }