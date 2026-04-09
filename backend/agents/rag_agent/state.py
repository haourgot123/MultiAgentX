from enum import Enum, auto
from typing import Any, List, Optional
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    file_name: str = ""
    file_id: int = 0
    page_no: Optional[int] = None
    metadata: dict = {}


class RAGAgentState(BaseModel):
    user_question: str
    memories: List[Any] = []
    user_id: int
    file_ids: List[int] = []
    transformed_query: str = ""
    retrieved_chunks: List[RetrievedChunk] = []
    reranked_chunks: List[RetrievedChunk] = []
    context: str = ""
    final_answer: str = ""


class Node(Enum):
    rag_agent_query_transform_node = auto()
    rag_agent_retrieve_node = auto()
    rag_agent_rerank_node = auto()
    rag_agent_synthesize_node = auto()
    rag_agent_stream_node = auto()


class Tag(Enum):
    retrieval_node = auto()
    context_node = auto()
    streaming_node = auto()