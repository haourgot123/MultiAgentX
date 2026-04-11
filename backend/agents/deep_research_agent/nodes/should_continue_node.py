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
        
        # --- Smart Continuation Logic ---
        
        # 1. Check basic iteration limit
        at_limit = current >= max_iter - 1
        
        # 2. Check for remaining knowledge gaps
        has_gaps = (
            len(state.analysis_notes) > 0 
            and any(len(note.strip()) > 0 for note in state.analysis_notes[-2:])
        ) if state.analysis_notes else False
        
        # 3. Check confidence levels — low confidence suggests more research needed
        low_confidence = False
        if state.findings:
            recent_confidences = [f.confidence for f in state.findings[-2:]]
            avg_confidence = sum(recent_confidences) / len(recent_confidences)
            low_confidence = avg_confidence < 0.6
        
        # 4. Coverage analysis — how many sub-questions have been addressed?
        covered_topics = set()
        if state.findings:
            for finding in state.findings:
                covered_topics.add(finding.topic.strip().lower())
        
        total_topics = len(state.research_plan) if state.research_plan else 1
        coverage_ratio = len(covered_topics) / total_topics if total_topics > 0 else 1.0
        low_coverage = coverage_ratio < 0.6
        
        # 5. Diminishing returns detection — if the latest iteration found very few new facts
        diminishing_returns = False
        if len(state.findings) >= 2:
            latest_facts = len(state.findings[-1].key_facts)
            prev_facts = len(state.findings[-2].key_facts)
            # If latest iteration found significantly fewer facts, diminishing returns
            diminishing_returns = latest_facts <= 1 and prev_facts <= 1
        
        # --- Decision ---
        should_continue = (
            not at_limit
            and not diminishing_returns
            and (has_gaps or low_confidence or low_coverage)
        )

        service_logger.info(
            f"Should continue decision: iteration {current + 1}/{max_iter}, "
            f"continue={should_continue}, gaps={has_gaps}, low_conf={low_confidence}, "
            f"coverage={coverage_ratio:.0%}, diminishing_returns={diminishing_returns}"
        )

        if should_continue:
            reason_parts = []
            if has_gaps:
                reason_parts.append("knowledge gaps remain")
            if low_confidence:
                reason_parts.append(f"confidence is low ({avg_confidence:.0%})")
            if low_coverage:
                reason_parts.append(f"only {coverage_ratio:.0%} of topics covered")
            reason = ", ".join(reason_parts) if reason_parts else "more research needed"
            
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_continue",
                    "message": f"Continuing research ({reason})... (iteration {current + 2}/{max_iter})",
                },
            )
        else:
            reason = "iteration limit" if at_limit else ("diminishing returns" if diminishing_returns else "sufficient coverage")
            dispatch_custom_event(
                "status",
                {
                    "step": "deep_research_continue",
                    "message": f"Research complete ({reason}). Synthesizing findings...",
                },
            )

        return {
            "current_iteration": current + 1,
            "need_more_research": should_continue,
        }