import base64
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

            if not result.urls and not result.base64_images:
                logger.error("[ImageGenerationAgent (GenerateNode)] No image URLs returned")
                return {
                    "error_message": "Image generation failed: No images were generated.",
                    "image_urls": [],
                }

            logger.info(
                "[ImageGenerationAgent (GenerateNode)] Generated "
                f"{len(result.urls) + len(result.base64_images)} images, uploading to blob storage..."
            )

            uploaded_assets = []
            if result.urls:
                uploaded_assets.extend(await self._upload_images_to_blob(result.urls, state.user_id))
            if result.base64_images:
                uploaded_assets.extend(
                    await self._upload_base64_images_to_blob(
                        result.base64_images,
                        state.user_id,
                        result.output_format,
                    )
                )

            sas_urls = [asset["url"] for asset in uploaded_assets if asset.get("url")]
            primary_blob_asset = next(
                (asset for asset in uploaded_assets if asset.get("blob_path")),
                {},
            )

            return {
                "image_urls": sas_urls,
                "revised_prompt": result.revised_prompt or "",
                "error_message": "",
                "blob_path": primary_blob_asset.get("blob_path", ""),
                "blob_name": primary_blob_asset.get("blob_name", ""),
                "blob_content_type": primary_blob_asset.get("blob_content_type", ""),
                "blob_size": primary_blob_asset.get("blob_size", 0),
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

    async def _upload_images_to_blob(self, temp_urls: list[str], user_id: int) -> list[dict[str, str | int]]:
        """Download images from temporary Azure OpenAI URLs and upload to blob storage.

        Returns asset metadata for each uploaded image.
        """
        uploaded_assets: list[dict[str, str | int]] = []
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
                    uploaded_assets.append(
                        {
                            "url": sas_url,
                            "blob_path": blob_path,
                            "blob_name": stored_name,
                            "blob_content_type": content_type,
                            "blob_size": len(response.content),
                        }
                    )
                    logger.info(f"[ImageGenerationAgent (GenerateNode)] Uploaded generated image to blob: {blob_path}")
                except Exception as exc:
                    logger.error(f"[ImageGenerationAgent (GenerateNode)] Failed to upload image to blob: {exc}")
                    # Fall back to the temporary URL so the response isn't empty
                    uploaded_assets.append(
                        {
                            "url": temp_url,
                            "blob_path": "",
                            "blob_name": "",
                            "blob_content_type": "",
                            "blob_size": 0,
                        }
                    )
        return uploaded_assets

    async def _upload_base64_images_to_blob(
        self,
        base64_images: list[str],
        user_id: int,
        output_format: str,
    ) -> list[dict[str, str | int]]:
        """Upload base64-encoded generated images to blob storage.

        Falls back to data URLs if blob upload fails.
        """
        uploaded_assets: list[dict[str, str | int]] = []
        normalized_format = (output_format or "png").lower()
        content_type = "image/jpeg" if normalized_format in {"jpg", "jpeg"} else f"image/{normalized_format}"
        ext = "jpg" if normalized_format in {"jpg", "jpeg"} else normalized_format

        for encoded_image in base64_images:
            try:
                image_bytes = base64.b64decode(encoded_image)
                stored_name = f"{uuid.uuid4().hex}.{ext}"
                blob_path = blob_storage_client.upload_file(
                    user_id=user_id,
                    stored_name=stored_name,
                    data=io.BytesIO(image_bytes),
                    content_type=content_type,
                )
                sas_url = blob_storage_client.generate_sas_url(blob_path, expiry_hours=24)
                uploaded_assets.append(
                    {
                        "url": sas_url,
                        "blob_path": blob_path,
                        "blob_name": stored_name,
                        "blob_content_type": content_type,
                        "blob_size": len(image_bytes),
                    }
                )
                logger.info(f"[ImageGenerationAgent (GenerateNode)] Uploaded generated image to blob: {blob_path}")
            except Exception as exc:
                logger.error(f"[ImageGenerationAgent (GenerateNode)] Failed to upload base64 image to blob: {exc}")
                uploaded_assets.append(
                    {
                        "url": f"data:{content_type};base64,{encoded_image}",
                        "blob_path": "",
                        "blob_name": "",
                        "blob_content_type": "",
                        "blob_size": 0,
                    }
                )

        return uploaded_assets
