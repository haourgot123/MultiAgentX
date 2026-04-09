from enum import auto
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel
from backend.agents.general_agent.tools.websearch import SearchResults


class GeneralAgentState(BaseModel):
    conversation_id: int
    user_id: int
    user_question: str
    time_now: str
    memories: List[Any]
    long_term_memory_context: Optional[str] = ""
    is_web_search_enabled: bool
    is_deep_research_enabled: bool
    is_generate_image_enabled: bool
    is_rag_enabled: bool = False
    file_ids: List[int] = []
    websearch_results: List[SearchResults] = []
    route: str = ""


class Node(Enum):
    general_agent_route_node = auto()
    general_agent_answer_node = auto()
    general_agent_memory_node = auto()
    general_agent_stream_node = auto()
    websearch_agent_transform_query_node = auto()
    websearch_agent_search_node = auto()
    websearch_agent_stream_node = auto()


class Tag(Enum):
    streaming_node = auto()
    explanation_node = auto()
    retrieval_progress_node = auto()
    direct_response_node = auto()