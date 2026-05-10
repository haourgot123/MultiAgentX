from typing import List, Optional
from openai import AzureOpenAI
from loguru import logger

from backend.config.settings import _settings

class ImageGenerationResult:
    def __init__(
        self,
        urls: List[str],
        base64_images: Optional[List[str]] = None,
        output_format: str = "png",
        revised_prompt: Optional[str] = None,
    ):
        self.urls = urls
        self.base64_images = base64_images or []
        self.output_format = output_format
        self.revised_prompt = revised_prompt


class ImageGenerationService:
    def __init__(self):
        self.api_key = _settings.azure_image_generation.api_key
        self.api_endpoint = _settings.azure_image_generation.api_endpoint
        self.api_version = _settings.azure_image_generation.api_version
        self.deployment_name = _settings.azure_image_generation.deployment_name
        self.default_size = _settings.azure_image_generation.default_size
        self.default_quality = _settings.azure_image_generation.default_quality
        self.default_n = _settings.azure_image_generation.default_n
        self._client = None

    def _get_client(self) -> AzureOpenAI:
        if self._client is None:
            if not self.api_key or not self.api_endpoint:
                raise ValueError("Image generation API key or endpoint not configured")
            self._client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.api_endpoint,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        n: Optional[int] = None,
    ) -> ImageGenerationResult:
        client = self._get_client()
        
        size = size or self.default_size
        quality = quality or self.default_quality
        n = n or self.default_n

        logger.info(f"[GeneralAgent (ImageGenerator)] Generating image with prompt: '{prompt[:100]}...'")

        try:
            result = client.images.generate(
                model=self.deployment_name,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )

            urls = [img.url for img in result.data if getattr(img, "url", None)]
            base64_images = [img.b64_json for img in result.data if getattr(img, "b64_json", None)]
            output_format = getattr(result, "output_format", "png") or "png"
            revised_prompt = result.data[0].revised_prompt if result.data else None

            logger.info(
                f"[GeneralAgent (ImageGenerator)] Generated {len(urls) + len(base64_images)} images "
                f"(urls={len(urls)}, base64={len(base64_images)})"
            )

            return ImageGenerationResult(
                urls=urls,
                base64_images=base64_images,
                output_format=output_format,
                revised_prompt=revised_prompt,
            )

        except Exception as e:
            logger.error(f"[GeneralAgent (ImageGenerator)] Image generation failed: {e}")
            raise

    async def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs,
    ) -> ImageGenerationResult:
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self.generate(prompt, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"[GeneralAgent (ImageGenerator)] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    continue
        raise last_error or Exception("Image generation failed after retries")


image_generation_service = ImageGenerationService()
