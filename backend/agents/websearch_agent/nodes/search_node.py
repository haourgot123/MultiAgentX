from typing import List
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger
from backend.agents.general_agent.tools.websearch import (
    TavilySearchService,
    SearchRequest,
)
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.websearch_agent.state import WebsearchAgentState


class SearchNode(Runnable):
    def __init__(self) -> None:
        """
        Initialize the SearchNode with a list of nodes
        """
        super().__init__()

    def invoke(self, state: WebsearchAgentState, **kwargs):
        pass

    def _deduplicate_results(self, results: List) -> List:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique_results = []
        for result in results:
            url = getattr(result, "url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
            elif not url:
                # Keep results without URLs (shouldn't happen but just in case)
                unique_results.append(result)
        return unique_results

    async def ainvoke(self, state: WebsearchAgentState, config: dict = None, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "websearch_search",
                "message": f"Starting web search ...",
            },
        )

        search_service = TavilySearchService()
        all_results = []
        successful_queries = 0
        failed_queries = 0

        # Process queries with progress tracking
        for i, query in enumerate(state.transformed_queries):
            progress_pct = int((i / len(state.transformed_queries)) * 100)

            try:
                results = await search_service.search(SearchRequest(query=query))
                if results:
                    all_results.extend(results)
                    successful_queries += 1
                    logger.info(f"Query '{query}' returned {len(results)} results")
                else:
                    logger.warning(f"Query '{query}' returned no results")
            except Exception as e:
                failed_queries += 1
                logger.error(f"Search failed for query '{query}': {e}")

        # Deduplicate results by URL
        unique_results = self._deduplicate_results(all_results)
        duplicates_removed = len(all_results) - len(unique_results)

        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate results")

        # Update state with deduplicated results
        state.search_results.extend(unique_results)

        # Summary dispatch
        dispatch_custom_event(
            "status",
            {
                "step": "websearch_search",
                "message": f"Search complete: {len(unique_results)} unique sources from queries",
            },
        )

        return {"search_results": state.search_results}
