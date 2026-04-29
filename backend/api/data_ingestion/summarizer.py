from __future__ import annotations

import asyncio
import base64
from typing import Any

from loguru import logger
from openai import AzureOpenAI, OpenAI

from backend.config.settings import _settings


class IngestionSummarizer:
    def __init__(self):
        config = _settings.ingestion_summary
        self.enabled = config.enabled
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.image_prompt = config.image_prompt
        self.table_prompt = config.table_prompt
        self.timeout_seconds = config.timeout_seconds
        self.max_concurrent = config.max_concurrent
        self._client: AzureOpenAI | OpenAI | None = None

    def _get_client(self) -> AzureOpenAI | OpenAI:
        if self._client is not None:
            return self._client

        azure_config = _settings.azure_chat_openai
        api_key = azure_config.api_key
        if not api_key:
            raise ValueError("Azure OpenAI API key is required for summarization")

        if azure_config.api_endpoint:
            self._client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_config.api_endpoint,
                api_version=azure_config.api_version,
                timeout=self.timeout_seconds,
            )
        else:
            self._client = OpenAI(
                api_key=api_key,
                base_url=_settings.openai_embedding.api_base,
                timeout=self.timeout_seconds,
            )
        return self._client

    def summarize_image(self, image_base64: str) -> str | None:
        if not self.enabled:
            return None
        try:
            client = self._get_client()
            if not image_base64.startswith("data:"):
                image_url = f"data:image/png;base64,{image_base64}"
            else:
                image_url = image_base64

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.image_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    }
                ],
                max_completion_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            if content:
                logger.debug(f"[IngestionSummarizer] Image summary generated: {len(content)} chars")
            return content
        except Exception as exc:
            logger.warning(f"[IngestionSummarizer] Failed to summarize image: {exc}")
            return None

    def summarize_table(self, table_markdown: str) -> str | None:
        if not self.enabled:
            return None
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a data analyst. Summarize tables concisely, "
                            "highlighting key information, structure, and notable patterns."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"{self.table_prompt}\n\n{table_markdown}",
                    },
                ],
                max_completion_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            if content:
                logger.debug(f"[IngestionSummarizer] Table summary generated: {len(content)} chars")
            return content
        except Exception as exc:
            logger.warning(f"[IngestionSummarizer] Failed to summarize table: {exc}")
            return None

    async def summarize_image_async(self, image_base64: str) -> str | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.summarize_image, image_base64)

    async def summarize_table_async(self, table_markdown: str) -> str | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.summarize_table, table_markdown)

    async def summarize_blocks_concurrently(
        self,
        blocks: list[dict[str, Any]],
    ) -> list[str | None]:
        if not self.enabled or not blocks:
            return [None] * len(blocks)

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _limited_summarize(block: dict[str, Any]) -> str | None:
            async with semaphore:
                block_type = block.get("block_type", "text")
                if block_type == "image":
                    image_data = block.get("image_data")
                    if image_data:
                        return await self.summarize_image_async(image_data)
                    return None
                elif block_type == "table":
                    table_text = block.get("text", "")
                    if table_text:
                        return await self.summarize_table_async(table_text)
                    return None
                return None

        tasks = [_limited_summarize(block) for block in blocks]
        return await asyncio.gather(*tasks)

    def summarize_blocks_sync(
        self,
        blocks: list[dict[str, Any]],
    ) -> list[str | None]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.summarize_blocks_concurrently(blocks),
                    )
                    return future.result(timeout=self.timeout_seconds * len(blocks))
            else:
                return loop.run_until_complete(
                    self.summarize_blocks_concurrently(blocks)
                )
        except RuntimeError:
            return asyncio.run(self.summarize_blocks_concurrently(blocks))


ingestion_summarizer = IngestionSummarizer()