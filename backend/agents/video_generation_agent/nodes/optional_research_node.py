from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.general_agent.tools.websearch import (
    SearchRequest,
    TavilySearchService,
)
from backend.agents.video_generation_agent.state import VideoGenerationAgentState


class OptionalResearchNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        if not state.web_search_enabled:
            return {"sources": []}

        await adispatch_custom_event(
            "status",
            {
                "step": "research",
                "message": "Searching for supporting context and visual references...",
            },
        )

        try:
            search_service = TavilySearchService()
            if not search_service.is_configured():
                logger.info(
                    "[VideoGenerationAgent (OptionalResearchNode)] "
                    "Skipping video research because Tavily search is not configured."
                )
                await adispatch_custom_event(
                    "status",
                    {
                        "step": "research",
                        "message": "Web research is not configured. Continuing with the prompt only...",
                    },
                )
                return {"sources": []}

            query = f"{state.prompt} visual references images"
            results = await search_service.search(
                SearchRequest(
                    query=query,
                    total_results=6,
                    include_images=True,
                    include_image_descriptions=True,
                )
            )
            image_count = sum(len(result.images) for result in results)
            await adispatch_custom_event(
                "status",
                {
                    "step": "research",
                    "message": f"Found {len(results)} source(s) and {image_count} image reference(s).",
                },
            )
            return {"sources": results}
        except Exception as exc:
            logger.opt(exception=exc).warning(
                "[VideoGenerationAgent (OptionalResearchNode)] "
                "Video research failed query={!r} error_type={} error={!r}",
                query if "query" in locals() else None,
                type(exc).__name__,
                exc,
            )
            await adispatch_custom_event(
                "status",
                {
                    "step": "research",
                    "message": "Research unavailable. Continuing with the prompt only...",
                },
            )
            return {"sources": []}
