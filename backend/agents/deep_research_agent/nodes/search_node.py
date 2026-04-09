from typing import List
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.deep_research_agent.state import (
    DeepResearchAgentState,
    SearchResult,
)
from backend.agents.general_agent.tools.websearch import (
    TavilySearchService,
    SearchRequest,
)


service_logger = logger.bind(service="deep-research-search")


class SearchNode(Runnable):
    def __init__(self):
        super().__init__()
        self.search_service = TavilySearchService()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_search",
                "message": f"🌐 Searching for information...",
            },
        )

        all_results: List[SearchResult] = []
        iteration = state.current_iteration

        service_logger.info(
            f"Executing {len(state.search_queries)} searches for iteration {iteration + 1}"
        )

        for i, query in enumerate(state.search_queries):
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_search",
                    "message": f"🔍 Searching: '{query[:40]}...'",
                },
            )

            try:
                search_request = SearchRequest(query=query, total_results=5)
                results = await self.search_service.search(search_request)

                for result in results:
                    search_result = SearchResult(
                        query=query,
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        source_type="web",
                        relevance_score=0.0,
                        iteration=iteration,
                    )
                    all_results.append(search_result)

                service_logger.info(
                    f"Query '{query[:30]}...' returned {len(results)} results"
                )

            except Exception as e:
                service_logger.error(f"Search failed for query '{query}': {e}")

        existing_urls = {r.url for r in state.search_results}
        new_results = [r for r in all_results if r.url not in existing_urls]

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_search",
                "message": f"✅ Found {len(new_results)} new results.",
            },
        )

        return {
            "search_results": [
                r.model_dump() for r in state.search_results + new_results
            ],
        }
