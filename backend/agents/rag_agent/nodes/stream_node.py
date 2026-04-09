from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, Tag


service_logger = logger.bind(service="rag-stream")


class StreamNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_stream",
                "message": "📤 Preparing final response...",
            },
        )

        service_logger.info("StreamNode: Preparing response")

        if not state.final_answer:
            state.final_answer = "I couldn't find relevant information in your documents to answer this question."

        dispatch_custom_event(
            "status",
            {
                "step": "rag_stream",
                "message": "✅ Response ready.",
            },
        )

        return {
            "output": state.final_answer,
        }