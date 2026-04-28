from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.general_agent.tools.websearch import (
    SearchRequest,
    TavilySearchService,
)
from backend.agents.video_generation_agent.state import VideoGenerationAgentState


service_logger = logger.bind(service="video-research")


class OptionalResearchNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        if not state.web_search_enabled:
            return {"sources": []}

        dispatch_custom_event(
            "status",
            {
                "step": "research",
                "message": "Searching for supporting context and visual references...",
            },
        )

        try:
            search_service = TavilySearchService()
            results = await search_service.search(
                SearchRequest(
                    query=f"{state.prompt} visual references images",
                    total_results=6,
                    include_images=True,
                    include_image_descriptions=True,
                )
            )
            image_count = sum(len(result.images) for result in results)
            dispatch_custom_event(
                "status",
                {
                    "step": "research",
                    "message": f"Found {len(results)} source(s) and {image_count} image reference(s).",
                },
            )
            return {"sources": results}
        except Exception as exc:
            service_logger.warning("Video research failed: {}", exc)
            dispatch_custom_event(
                "status",
                {
                    "step": "research",
                    "message": "Research unavailable. Continuing with the prompt only...",
                },
            )
            return {"sources": []}
