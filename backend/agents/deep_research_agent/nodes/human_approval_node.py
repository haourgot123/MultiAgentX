from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState


service_logger = logger.bind(service="deep-research-human-approval")


class HumanApprovalNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_approval",
                "message": "⚠️ Awaiting human approval for research plan...",
            },
        )

        service_logger.info(f"HumanApprovalNode: Checking if plan is approved")

        # This node acts as a checkpoint
        # If plan_approved is False, graph will pause here (LangGraph interrupt)
        # When user approves, graph will resume with plan_approved=True and approved_plan set
        
        if not state.plan_approved:
            service_logger.info("Plan not yet approved, waiting for human input")
            # In LangGraph, this would trigger an interrupt
            # But we'll just return empty state to continue
            # The actual interrupt will be handled at the graph level
        
        if state.approved_plan:
            service_logger.info(f"Plan approved with {len(state.approved_plan)} questions")
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_approval",
                    "message": f"✅ Research plan approved. Starting investigation.",
                },
            )
            return {
                "research_plan": state.approved_plan,
            }
        
        return {}