from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState


service_logger = logger.bind(service="deep-research-continue")


class ShouldContinueNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        current = state.current_iteration
        max_iter = state.max_iterations
        
        need_more = state.need_more_research
        
        has_gaps = len(state.analysis_notes) > 0 and len(state.analysis_notes[-1]) > 0 if state.analysis_notes else False
        
        low_confidence = state.findings and state.findings[-1].confidence < 0.6 if state.findings else False
        
        should_continue = (
            current < max_iter - 1
            and (need_more or has_gaps or low_confidence)
        )

        service_logger.info(
            f"Should continue decision: iteration {current + 1}/{max_iter}, "
            f"continue={should_continue}, gaps={has_gaps}, low_conf={low_confidence}"
        )

        if should_continue:
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_continue",
                    "message": f"🔄 Continuing research... (iteration {current + 2}/{max_iter})",
                },
            )
        else:
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_continue",
                    "message": "✅ Research complete. Synthesizing findings...",
                },
            )

        return {
            "current_iteration": current + 1,
            "need_more_research": should_continue,
        }