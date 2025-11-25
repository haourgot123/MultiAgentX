from langchain_tavily import TavilySearch
from app.config.settings import _settings





class TavilyWebSearch:
    """
    Web search tool using LangChain Tavily for real-time internet search with domain restrictions.
    """
    def __init__(self):
        self.tavily_search = TavilySearch(
            max_results=_settings.tavily_search.max_results,
            include_answer=_settings.tavily_search.include_answer,
            search_depth=_settings.tavily_search.search_depth,
            api_key=_settings.tavily_search.api_key,
            allowed_domains=_settings.tavily_search.allowed_domains,
            exclude_domains=_settings.tavily_search.exclude_domains
        )
        
    def invoke(self, query: str) -> str:
        search_params = {"query": query, "search_depth": _settings.tavily_search.search_depth}
        try:
            return self.tavily_search.invoke(search_params)
        except TypeError:
            return self.tavily_search.invoke(query)
    async def ainvoke(self, query: str) -> str:
        search_params = {"query": query, "search_depth": _settings.tavily_search.search_depth}
        try:
            return await self.tavily_search.ainvoke(search_params)
        except TypeError:
            return await self.tavily_search.ainvoke(query)