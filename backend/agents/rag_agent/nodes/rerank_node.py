from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.rag import RAG_PROMPTS


service_logger = logger.bind(service="rag-rerank")


class RerankedChunks(BaseModel):
    reranked_indices: list[int] = Field(description="indices of chunks in order of relevance (most relevant first)")
    reasoning: str = Field(description="brief explanation of reranking decision")
    relevance_scores: list[float] = Field(
        default_factory=list,
        description="relevance scores (0-10) for each chunk in the reranked order"
    )


class RerankNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_rerank",
                "message": "Re-ranking results by relevance...",
            },
        )

        if not state.retrieved_chunks:
            service_logger.warning("No chunks to rerank")
            return {"reranked_chunks": []}

        # For small chunk sets (<=3), skip LLM reranking — use original order
        if len(state.retrieved_chunks) <= 3:
            service_logger.info(f"Only {len(state.retrieved_chunks)} chunks, skipping LLM rerank")
            dispatch_custom_event(
                "status",
                {
                    "step": "rag_rerank",
                    "message": f"Using {len(state.retrieved_chunks)} retrieved passages (small set, no rerank needed).",
                },
            )
            return {"reranked_chunks": [c.model_dump() for c in state.retrieved_chunks]}

        service_logger.info(f"Reranking {len(state.retrieved_chunks)} chunks")

        # Build chunks text with metadata for better reranking context
        chunks_text = "\n\n".join([
            (
                f"[{idx}] "
                + (f"(File: {chunk.file_name}" + (f", Page {chunk.page_no}" if chunk.page_no else "") + ") " if chunk.file_name else "")
                + f"{chunk.text[:600]}..."
            )
            for idx, chunk in enumerate(state.retrieved_chunks[:12])
        ])

        messages = [
            SystemMessage(content=RAG_PROMPTS["RERANK_SYSTEM"]),
            HumanMessage(content=RAG_PROMPTS["RERANK_USER"].format(
                user_question=state.user_question,
                chunks_text=chunks_text,
            )),
        ]

        try:
            llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(RerankedChunks)
            result = await llm_with_structure.ainvoke(messages)
            
            # Build reranked list from indices
            reranked_chunks = []
            seen_indices = set()
            for idx in result.reranked_indices[:8]:  # Keep top 8
                if 0 <= idx < len(state.retrieved_chunks) and idx not in seen_indices:
                    reranked_chunks.append(state.retrieved_chunks[idx])
                    seen_indices.add(idx)
            
            # Append any remaining chunks not in the reranked list (as fallback)
            for i, chunk in enumerate(state.retrieved_chunks):
                if i not in seen_indices:
                    reranked_chunks.append(chunk)
            
            service_logger.info(f"Reranked to {len(reranked_chunks)} chunks. Reasoning: {result.reasoning[:100]}")

            dispatch_custom_event(
                "status",
                {
                    "step": "rag_rerank",
                    "message": f"Re-ranked {len(reranked_chunks)} passages by relevance.",
                },
            )

            return {"reranked_chunks": [c.model_dump() for c in reranked_chunks]}

        except Exception as e:
            service_logger.error(f"Reranking failed: {e}")
            # Graceful degradation: return original order
            return {"reranked_chunks": [c.model_dump() for c in state.retrieved_chunks]}