import io
import uuid

import httpx
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.agents.general_agent.tools.image_generator import image_generation_service
from backend.utils.blob_storage import blob_storage_client
from backend.agents.utils import astream_custom_event



class GenerateNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: ImageGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: ImageGenerationAgentState, **kwargs):
        await astream_custom_event(
            event_name="status",
            step="image_generate",
            message="Generating image...",
        )

        prompt = state.enhanced_prompt if state.enhanced_prompt else state.user_question

        logger.info(f"[ImageGenerationAgent (GenerateNode)] Generating image for prompt: '{prompt[:100]}...'")

        try:
            result = await image_generation_service.generate_with_retry(
                prompt=prompt,
                max_retries=3,
            )

            if not result.urls:
                logger.error("[ImageGenerationAgent (GenerateNode)] No image URLs returned")
                return {
                    "error_message": "Image generation failed: No images were generated.",
                    "image_urls": [],
                }

            logger.info(f"[ImageGenerationAgent (GenerateNode)] Generated {len(result.urls)} images, uploading to blob storage...")

            sas_urls = await self._upload_images_to_blob(result.urls, state.user_id)

            return {
                "image_urls": sas_urls,
                "revised_prompt": result.revised_prompt or "",
                "error_message": "",
            }

        except Exception as e:
            logger.error(f"[ImageGenerationAgent (GenerateNode)] Image generation error: {e}")
            await astream_custom_event(
                event_name="status",
                step="image_generate",
                message="Image generation failed.",
            )
            return {
                "error_message": f"Image generation failed: {str(e)}",
                "image_urls": [],
            }

    async def _upload_images_to_blob(self, temp_urls: list[str], user_id: int) -> list[str]:
        """Download images from temporary Azure OpenAI URLs and upload to blob storage.

        Returns a list of permanent SAS URLs.
        """
        sas_urls: list[str] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for temp_url in temp_urls:
                try:
                    response = await client.get(temp_url)
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "image/png").split(";")[0].strip()
                    ext = "png" if "png" in content_type else "jpg"
                    stored_name = f"{uuid.uuid4().hex}.{ext}"

                    blob_path = blob_storage_client.upload_file(
                        user_id=user_id,
                        stored_name=stored_name,
                        data=io.BytesIO(response.content),
                        content_type=content_type,
                    )
                    sas_url = blob_storage_client.generate_sas_url(blob_path, expiry_hours=24)
                    sas_urls.append(sas_url)
                    logger.info(f"[ImageGenerationAgent (GenerateNode)] Uploaded generated image to blob: {blob_path}")
                except Exception as exc:
                    logger.error(f"[ImageGenerationAgent (GenerateNode)] Failed to upload image to blob: {exc}")
                    # Fall back to the temporary URL so the response isn't empty
                    sas_urls.append(temp_url)
        return sas_urls