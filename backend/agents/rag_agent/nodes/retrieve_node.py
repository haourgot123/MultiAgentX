import asyncio
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk
from backend.agents.general_agent.tools.retriever import hybrid_retriever


service_logger = logger.bind(service="rag-retrieve")


def _deduplicate_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Merge duplicate chunk_ids, keeping the highest score."""
    seen: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        if chunk.chunk_id not in seen or chunk.score > seen[chunk.chunk_id].score:
            seen[chunk.chunk_id] = chunk
    deduped = sorted(seen.values(), key=lambda c: c.score, reverse=True)
    return deduped


class RetrieveNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_retrieve",
                "message": "Searching documents with multiple queries...",
            },
        )

        # Use all transformed queries; fall back to primary or raw question
        queries: list[str] = state.transformed_queries or (
            [state.transformed_query] if state.transformed_query else [state.user_question]
        )

        service_logger.info(
            f"Retrieving with {len(queries)} queries: "
            + " | ".join(f"[{i+1}] '{q[:60]}'" for i, q in enumerate(queries))
        )

        # Run all queries concurrently
        search_tasks = [
            hybrid_retriever.search(
                query=q,
                user_id=state.user_id,
                file_ids=state.file_ids if state.file_ids else None,
            )
            for q in queries
        ]
        search_results = await asyncio.gather(*search_tasks)

        # Collect and deduplicate across all query results
        all_chunks: list[RetrievedChunk] = []
        for result in search_results:
            all_chunks.extend(result.merged_results)

        retrieved_chunks = _deduplicate_chunks(all_chunks)

        service_logger.info(
            f"Retrieved {len(retrieved_chunks)} unique chunks from {len(queries)} queries"
        )

        if retrieved_chunks:
            sources_preview = ", ".join([c.file_name or f"chunk_{c.chunk_id[:8]}" for c in retrieved_chunks[:3]])
            dispatch_custom_event(
                "status",
                {
                    "step": "rag_retrieve",
                    "message": f"Found relevant passages ...",
                },
            )
        else:
            dispatch_custom_event(
                "status",
                {
                    "step": "rag_retrieve",
                    "message": "No relevant documents found in knowledge base.",
                },
            )

        return {
            "retrieved_chunks": [chunk.model_dump() for chunk in retrieved_chunks],
        }