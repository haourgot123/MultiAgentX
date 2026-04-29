from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.agents.utils import astream_custom_event

class HumanApprovalNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        await astream_custom_event(
            event_name="status",
            step="deep_research_approval",
            message="Awaiting human approval for research plan...",
        )

        logger.info(f"[DeepResearchAgent (HumanApprovalNode)] Checking if plan is approved")

        # This node acts as a checkpoint
        # If plan_approved is False, graph will pause here (LangGraph interrupt)
        # When user approves, graph will resume with plan_approved=True and approved_plan set
        
        if not state.plan_approved:
            logger.info("[DeepResearchAgent (HumanApprovalNode)] Plan not yet approved, waiting for human input")
            # In LangGraph, this would trigger an interrupt
            # But we'll just return empty state to continue
            # The actual interrupt will be handled at the graph level
        
        if state.approved_plan:
            logger.info(f"[DeepResearchAgent (HumanApprovalNode)] Plan approved with {len(state.approved_plan)} questions")
            await astream_custom_event(
                event_name="status",
                step="deep_research_approval",
                message="Research plan approved. Starting investigation.",
            )
            return {
                "research_plan": state.approved_plan,
            }
        
        return {}