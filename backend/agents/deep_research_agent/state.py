from enum import Enum, auto
from typing import Any, List, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    query: str
    title: str
    url: str
    snippet: str
    source_type: str = "web"
    relevance_score: float = 0.0
    iteration: int = 0


class ResearchFinding(BaseModel):
    topic: str
    key_facts: List[str]
    sources: List[str]
    confidence: float = 0.0


class DeepResearchAgentState(BaseModel):
    user_question: str
    memories: List[Any] = []
    research_plan: List[str] = []
    approved_plan: List[str] = []
    plan_approved: bool = False
    current_iteration: int = 0
    max_iterations: int = 3
    search_queries: List[str] = []
    search_results: List[SearchResult] = []
    findings: List[ResearchFinding] = []
    analysis_notes: List[str] = []
    need_more_research: bool = True
    final_report: str = ""
    output: str = ""
    current_task: str = ""


class Node(Enum):
    deep_research_agent_plan_node = auto()
    deep_research_agent_query_generation_node = auto()
    deep_research_agent_search_node = auto()
    deep_research_agent_analyze_node = auto()
    deep_research_agent_should_continue_node = auto()
    deep_research_agent_synthesize_node = auto()
    deep_research_agent_stream_node = auto()


class Tag(Enum):
    streaming_node = auto()
    research_node = auto()
    analysis_node = auto()
