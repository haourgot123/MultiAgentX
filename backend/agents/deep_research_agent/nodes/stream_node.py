import asyncio
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState


service_logger = logger.bind(service="deep-research-stream")


class StreamNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        service_logger.info("StreamNode: Starting to stream response")
        
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_stream",
                "message": "📤 Preparing final output...",
            },
        )

        service_logger.info("StreamNode: Preparing response")

        if not state.final_report:
            service_logger.warning("StreamNode: No final_report in state, using fallback message")
            output = "I apologize, but I couldn't complete the research. Please try again with a more specific question."
        else:
            service_logger.info(f"StreamNode: Final report length: {len(state.final_report)} characters")
            output = state.final_report

        # Stream the output token by token with status update
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_stream",
                "message": "✅ Deep research complete. Streaming results...",
            },
        )

        service_logger.info("StreamNode: Emitting token event")
        
        # Emit the entire output as a token event
        dispatch_custom_event(
            "token",
            {
                "delta": output,
            },
        )

        service_logger.info("StreamNode: Finished streaming response")
        
        return {
            "output": output,
        }