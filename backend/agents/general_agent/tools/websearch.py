from langchain.tools import tool
from abc import ABC, abstractmethod
from backend.config.settings import _settings
import httpx
from pydantic import BaseModel
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command


class SearchResults(BaseModel):
    title: str
    url: str
    snippet: str

class SearchRequest(BaseModel):
    query: str
    total_results: int = 4

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

    async def search(self, search_request: SearchRequest) -> list[SearchResults]:
        params = {
            "query": search_request.query,
            "max_results": search_request.total_results,
            "include_answer": self.tavily_search_include_answer,
            "search_depth": self.tavily_search_search_depth,
            "exclude_domains": self.tavily_search_exclude_domains
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.tavily_search_url, 
                json=params, 
                timeout=10.0, 
                headers={
                    "Authorization": f"Bearer {self.tavily_search_api_key}",
                    "Content-Type": "application/json"
                }
            )

        if response.status_code == 200:
            response_json = response.json()
            items = response_json.get("results", [])
            return [
                SearchResults(
                    title=item.get("title"), 
                    url=item.get("url"), 
                    snippet=item.get("content")
                ) 
                for item in items
            ]
            
        else:
            raise httpx.HTTPStatusError(
                f"HTTP {response.status_code}", request=response.request, response=response
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