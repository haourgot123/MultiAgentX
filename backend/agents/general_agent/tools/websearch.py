from langchain.tools import tool
from abc import ABC, abstractmethod
from backend.config.settings import _settings
import httpx
from pydantic import BaseModel, Field
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command


class SearchResults(BaseModel):
    title: str
    url: str
    snippet: str
    images: list[str] = Field(default_factory=list)

class SearchRequest(BaseModel):
    query: str
    total_results: int = 4
    include_images: bool = False
    include_image_descriptions: bool = False
    search_depth: str | None = None

class SearchServiceBase(ABC):
    @abstractmethod
    def search(self, search_request: SearchRequest) -> list[SearchResults]:
        ...

class GoogleSearchService(SearchServiceBase):
    def __init__(self):
        self.gg_search_url = _settings.gg_search.gg_search_url
        self.gg_search_engine_id = _settings.gg_search.gg_search_engine_id

    async def search(self, search_request: SearchRequest) -> list[SearchResults]:
        
        params = {
            "q": search_request.query,
            "cx": self.gg_search_engine_id,
            "num": search_request.total_results
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(self.gg_search_url, params=params, timeout=10.0)

        if response.status_code == 200:
            response_json = response.json() 
            items = response_json.get("items", [])
            return [
               SearchResults(
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                )
                for item in items
            ]

        # Raise HTTPStatusError for non-200. Decorator decides to rotate only on 403/429.
        raise httpx.HTTPStatusError(
            f"HTTP {response.status_code}", request=response.request, response=response
        )

class TavilySearchService(SearchServiceBase):
    def __init__(self):
        self.tavily_search_url = _settings.tavily_search.api_endpoint
        self.tavily_search_api_key = _settings.tavily_search.api_key
        self.tavily_search_include_answer = _settings.tavily_search.include_answer
        self.tavily_search_search_depth = _settings.tavily_search.search_depth
        self.tavily_search_exclude_domains = _settings.tavily_search.exclude_domains

    def is_configured(self) -> bool:
        return bool(self.tavily_search_url and self.tavily_search_api_key)

    @staticmethod
    def _extract_image_urls(raw_images) -> list[str]:
        urls: list[str] = []
        if not isinstance(raw_images, list):
            return urls

        for image in raw_images:
            if isinstance(image, str):
                url = image
            elif isinstance(image, dict):
                url = image.get("url") or image.get("src") or ""
            else:
                url = ""

            if isinstance(url, str) and url.startswith(("http://", "https://")):
                urls.append(url)
        return urls

    async def search(self, search_request: SearchRequest) -> list[SearchResults]:
        if not self.is_configured():
            raise RuntimeError(
                "Tavily search is not configured: missing TAVILY_SEARCH_API_ENDPOINT or TAVILY_SEARCH_API_KEY"
            )

        params = {
            "query": search_request.query,
            "max_results": search_request.total_results,
            "include_answer": self.tavily_search_include_answer,
            "search_depth": search_request.search_depth or self.tavily_search_search_depth,
            "exclude_domains": self.tavily_search_exclude_domains,
            "include_images": search_request.include_images,
            "include_image_descriptions": search_request.include_image_descriptions,
        }

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    self.tavily_search_url,
                    json=params,
                    timeout=_settings.tavily_search.timeout_seconds,
                    headers={
                        "Authorization": f"Bearer {self.tavily_search_api_key}",
                        "Content-Type": "application/json"
                    }
                )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Tavily request failed for query={search_request.query!r} endpoint={self.tavily_search_url!r}: {exc!r}"
            ) from exc

        if response.status_code == 200:
            response_json = response.json()
            items = response_json.get("results", [])
            top_level_images = self._extract_image_urls(response_json.get("images", []))
            results = [
                SearchResults(
                    title=item.get("title"), 
                    url=item.get("url"), 
                    snippet=item.get("content"),
                    images=self._extract_image_urls(item.get("images", [])),
                ) 
                for item in items
            ]

            if top_level_images:
                if results:
                    merged = list(dict.fromkeys([*results[0].images, *top_level_images]))
                    results[0].images = merged
                else:
                    results.append(
                        SearchResults(
                            title=f"Images for {search_request.query}",
                            url="",
                            snippet="Image search results",
                            images=top_level_images,
                        )
                    )

            return results
            
        else:
            response_preview = response.text[:500].replace("\n", " ").strip()
            raise httpx.HTTPStatusError(
                (
                    f"Tavily HTTP {response.status_code} for query={search_request.query!r} "
                    f"endpoint={self.tavily_search_url!r} response={response_preview!r}"
                ),
                request=response.request,
                response=response,
            )
            

WEBSEARCH_TOOL_DESCRIPTION = """
Search the internet using Google to retrieve relevant information.

Use this tool when the user asks for information that requires web access or up-to-date knowledge.

Arguments:
- query: the search query
- total_results: number of results to return
"""

@tool
async def websearch(
    query: str, 
    runtime: ToolRuntime
) -> Command:
    """
    Search the internet using Google to retrieve relevant information.

    Use this tool when the user asks for information that requires web access or up-to-date knowledge.

    Arguments:
    - query: the search query
    - total_results: number of results to return

    Returns:
    - websearch_results: list of search results
    """
    
    writer = runtime.stream_writer
    writer("Searching the internet for information...")
    search_engine = TavilySearchService()
    search_request = SearchRequest(query=query)
    results = await search_engine.search(search_request)
    for result in results:
        writer(f"Searching: {result.title} - {result.url}")
    return Command(update={
        "websearch_results": results
    })
