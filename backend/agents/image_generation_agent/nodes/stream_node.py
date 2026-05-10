from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.agents.utils import astream_custom_event



class StreamNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: ImageGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: ImageGenerationAgentState, **kwargs):
        await astream_custom_event(
            event_name="status",
            step="image_stream",
            message="Preparing image response...",
        )

        logger.info("[ImageGenerationAgent (StreamNode)] Preparing response")

        if state.error_message:
            output = (
                f"I apologize, but I couldn't generate the image.\n\n"
                f"**Error:** {state.error_message}\n\n"
                f"Please try:\n"
                f"- Using a different description\n"
                f"- Simplifying the prompt\n"
                f"- Avoiding restricted content"
            )
        elif state.image_urls:
            if len(state.image_urls) == 1:
                output = f"Here's your generated image:\n\n![Generated Image]({state.image_urls[0]})\n\n"
            else:
                output = f"Here are the {len(state.image_urls)} generated images:\n\n"
                for i, url in enumerate(state.image_urls, 1):
                    output += f"**Image {i}:**\n\n![Image {i}]({url})\n\n"
            
            # Add the revised prompt info if available
            if state.revised_prompt:
                output += f"\n---\n*Prompt used by the model: \"{state.revised_prompt[:300]}\"*"
        else:
            output = (
                "I wasn't able to generate any images. This might be due to a temporary service issue.\n\n"
                "Please try again with a different description."
            )

        await astream_custom_event(
            event_name="token",
            step="image_stream",
            message="Streaming image response...",
            delta=output,
        )

        return {
            "output": output,
        }
