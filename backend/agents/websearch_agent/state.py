from typing import List, Any
from pydantic import BaseModel
from backend.agents.general_agent.tools.websearch import SearchResults

class WebsearchAgentState(BaseModel):
    user_question: str
    search_query: str
    memories: List[Any] = []
    transformed_queries: List[str] = []
    search_results: List[SearchResults] = []
