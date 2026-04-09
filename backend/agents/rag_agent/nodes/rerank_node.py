from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="rag-rerank")


class RerankedChunks(BaseModel):
    reranked_indices: list[int] = Field(description="indices of chunks in order of relevance")
    reasoning: str = Field(description="brief explanation of reranking decision")


RERANK_SYSTEM = """You are a document relevance ranking expert.
Your task is to re-rank retrieved document chunks based on their relevance to the user's question.

Guidelines:
1. Most relevant chunks should come first
2. Consider both semantic relevance and factual accuracy
3. Prioritize chunks that directly answer the question
4. Remove chunks that are completely irrelevant
5. Keep the original chunk indices for reference

Return the indices in order of relevance (most relevant first)."""


RERANK_USER = """User Question: {user_question}

Retrieved Chunks (with indices):
{chunks_text}

Re-rank these chunks by relevance and provide the indices in order."""


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
                "message": "🎯 Re-ranking results by relevance...",
            },
        )

        if not state.retrieved_chunks:
            service_logger.warning("No chunks to rerank")
            return {"reranked_chunks": []}

        service_logger.info(f"Reranking {len(state.retrieved_chunks)} chunks")

        chunks_text = "\n\n".join([
            f"[{idx}] {chunk.text[:500]}..."
            for idx, chunk in enumerate(state.retrieved_chunks[:10])
        ])

        messages = [
            SystemMessage(content=RERANK_SYSTEM),
            HumanMessage(content=RERANK_USER.format(
                user_question=state.user_question,
                chunks_text=chunks_text,
            )),
        ]

        try:
            llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(RerankedChunks)
            result = await llm_with_structure.ainvoke(messages)
            
            reranked_chunks = []
            for idx in result.reranked_indices[:5]:
                if 0 <= idx < len(state.retrieved_chunks):
                    reranked_chunks.append(state.retrieved_chunks[idx])
            
            for chunk in state.retrieved_chunks:
                if chunk not in reranked_chunks:
                    reranked_chunks.append(chunk)
            
            service_logger.info(f"Reranked to {len(reranked_chunks)} chunks")

            dispatch_custom_event(
                "status",
                {
                    "step": "rag_rerank",
                    "message": f"✅ Re-ranked {len(reranked_chunks)} most relevant passages.",
                },
            )

            return {"reranked_chunks": [c.model_dump() for c in reranked_chunks]}

        except Exception as e:
            service_logger.error(f"Reranking failed: {e}")
            return {"reranked_chunks": [c.model_dump() for c in state.retrieved_chunks]}