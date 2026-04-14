from enum import Enum, auto
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    file_name: str = ""
    file_id: int = 0
    page_no: Optional[int] = None
    chunk_index: int = 0
    bbox_json: str = ""
    metadata: dict = {}


class RAGAgentState(BaseModel):
    user_question: str
    memories: List[Any] = []
    user_id: int
    conversation_id: int = 0
    file_ids: List[int] = []

    # Query transform
    transformed_query: str = ""
    transformed_queries: List[str] = []  # All 3 generated queries for multi-query retrieval

    # Retrieval
    retrieved_chunks: List[RetrievedChunk] = []

    # Combine context
    combined_context: str = ""
    citation_map: Dict[str, dict] = {}  # {citation_label: {chunk_id, file_id, ...}}

    # Evaluation loop
    is_relevant: bool = False
    retry_count: int = 0
    max_retries: int = 3
    evaluation_feedback: str = ""  # Feedback from evaluation for query re-transform

    # Synthesis
    final_answer: str = ""


class Node(Enum):
    rag_agent_query_transform_node = auto()
    rag_agent_retrieve_node = auto()
    rag_agent_combine_context_node = auto()
    rag_agent_evaluation_node = auto()
    rag_agent_synthesize_node = auto()


class Tag(Enum):
    retrieval_node = auto()
    context_node = auto()
    streaming_node = auto()