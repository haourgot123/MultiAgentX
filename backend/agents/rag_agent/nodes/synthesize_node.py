from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="rag-synthesize")


SYNTHESIZE_SYSTEM = """You are a knowledgeable assistant that answers questions based on retrieved document context.
Your task is to provide accurate, comprehensive answers using ONLY the information from the provided context.

Guidelines:
1. Answer the question directly and comprehensively
2. Cite sources using [Document X] format where X is the file name
3. If the context doesn't contain enough information, clearly state what's missing
4. Don't make up information not present in the context
5. Be concise but thorough
6. Use the same language as the user's question

When citing, use format: [File: filename] or [Page X] when available."""


SYNTHESIZE_USER = """User Question: {user_question}

Context from retrieved documents:
{context}

Please provide a comprehensive answer based on the context above. Include citations where appropriate."""


class SynthesizeNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "📝 Synthesizing answer from documents...",
            },
        )

        chunks = state.reranked_chunks if state.reranked_chunks else state.retrieved_chunks

        if not chunks:
            service_logger.warning("No chunks to synthesize")
            return {
                "context": "",
                "final_answer": "I apologize, but I couldn't find any relevant information in your documents to answer this question. Please try rephrasing your question or check if the relevant documents have been uploaded to the knowledge base.",
            }

        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            chunk_obj = RetrievedChunk(**chunk) if isinstance(chunk, dict) else chunk
            source = f"[{i+1}]"
            if chunk_obj.file_name:
                source = f"[{i+1}] File: {chunk_obj.file_name}"
                if chunk_obj.page_no:
                    source += f", Page {chunk_obj.page_no}"
            context_parts.append(f"{source}\n{chunk_obj.text}")

        context = "\n\n---\n\n".join(context_parts)

        service_logger.info(f"Synthesizing from {len(chunks)} chunks")

        messages = [
            SystemMessage(content=SYNTHESIZE_SYSTEM),
            HumanMessage(content=SYNTHESIZE_USER.format(
                user_question=state.user_question,
                context=context[:8000],
            )),
        ]

        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "✍️ Generating answer...",
            },
        )

        response = await azure_chat_openai_gpt_5_1.ainvoke(messages)
        final_answer = response.content

        service_logger.info(f"Synthesized answer of {len(final_answer)} characters")

        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "✅ Answer synthesized successfully.",
            },
        )

        return {
            "context": context,
            "final_answer": final_answer,
        }