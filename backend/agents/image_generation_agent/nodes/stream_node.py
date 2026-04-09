from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState


service_logger = logger.bind(service="image-stream")


class StreamNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: ImageGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: ImageGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "image_stream",
                "message": "📤 Preparing image response...",
            },
        )

        service_logger.info("StreamNode: Preparing response")

        if state.error_message:
            output = f"I apologize, but I couldn't generate the image. Error: {state.error_message}"
        elif state.image_urls:
            if len(state.image_urls) == 1:
                output = f"Here's the generated image:\n\n![Generated Image]({state.image_urls[0]})\n\n"
            else:
                output = f"Here are the {len(state.image_urls)} generated images:\n\n"
                for i, url in enumerate(state.image_urls, 1):
                    output += f"![Image {i}]({url})\n\n"
            
            if state.revised_prompt:
                output += f"\n*Revised prompt used: \"{state.revised_prompt[:200]}...\"*"
        else:
            output = "I wasn't able to generate any images. Please try again with a different description."

        dispatch_custom_event(
            "status",
            {
                "step": "image_stream",
                "message": "✅ Image response ready.",
            },
        )

        return {
            "output": output,
        }