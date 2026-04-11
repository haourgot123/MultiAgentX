from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState
from backend.agents.general_agent.tools.retriever import hybrid_retriever, RetrievedChunk


service_logger = logger.bind(service="rag-retrieve")


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
                "message": "Searching documents...",
            },
        )

        service_logger.info(f"Retrieving documents for query: '{state.transformed_query[:100] if state.transformed_query else state.user_question[:100]}...'")

        query = state.transformed_query if state.transformed_query else state.user_question
        
        search_result = await hybrid_retriever.search(
            query=query,
            user_id=state.user_id,
            file_ids=state.file_ids if state.file_ids else None,
        )

        retrieved_chunks = search_result.merged_results

        service_logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        if retrieved_chunks:
            sources_preview = ", ".join([c.file_name or f"chunk_{c.chunk_id[:8]}" for c in retrieved_chunks[:3]])
            dispatch_custom_event(
                "status",
                {
                    "step": "rag_retrieve",
                    "message": f"Found {len(retrieved_chunks)} relevant passages from: {sources_preview}...",
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