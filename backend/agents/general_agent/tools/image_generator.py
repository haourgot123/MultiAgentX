from typing import List, Optional
from openai import AzureOpenAI
from loguru import logger

from backend.config.settings import _settings


service_logger = logger.bind(service="image-generator")


class ImageGenerationResult:
    def __init__(self, urls: List[str], revised_prompt: Optional[str] = None):
        self.urls = urls
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

        service_logger.info(f"Generating image with prompt: '{prompt[:100]}...'")

        try:
            result = client.images.generate(
                model=self.deployment_name,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )

            urls = [img.url for img in result.data if img.url]
            revised_prompt = result.data[0].revised_prompt if result.data else None

            service_logger.info(f"Generated {len(urls)} images")

            return ImageGenerationResult(urls=urls, revised_prompt=revised_prompt)

        except Exception as e:
            service_logger.error(f"Image generation failed: {e}")
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
                service_logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    continue
        raise last_error or Exception("Image generation failed after retries")


image_generation_service = ImageGenerationService()