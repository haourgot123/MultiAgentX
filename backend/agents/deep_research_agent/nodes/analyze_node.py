from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState, SearchResult, ResearchFinding
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.deep_research import DEEP_RESEARCH_PROMPTS


service_logger = logger.bind(service="deep-research-analyze")


class AnalysisResult(BaseModel):
    key_findings: List[str] = Field(description="key facts and insights extracted (3-7 items)")
    knowledge_gaps: List[str] = Field(description="areas needing more research")
    confidence: float = Field(description="confidence level 0.0-1.0 for this analysis iteration")
    contradictions: List[str] = Field(
        default_factory=list,
        description="any contradictions found between sources"
    )
    evidence_strength: str = Field(
        default="moderate",
        description="overall evidence strength: strong, moderate, or weak"
    )


ANALYZE_USER = """Analyze these search results for the research question:

Main Question: {user_question}
Current Focus: {current_task}

Search Results from this iteration:
{search_results}

Previous Findings from earlier iterations:
{previous_findings}

Previously Identified Knowledge Gaps:
{previous_gaps}

Instructions:
1. Extract 3-7 key findings, noting the evidence quality for each
2. Identify any contradictions between sources
3. Assess the overall evidence strength (strong/moderate/weak)
4. Identify 1-3 specific knowledge gaps that remain
5. Rate your confidence (0.0-1.0) in these findings
6. Consider source credibility (official > news > blog > forum)"""


class AnalyzeNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_analyze",
                "message": "Analyzing findings with credibility assessment...",
            },
        )

        iteration = state.current_iteration
        
        # Get results from current iteration
        new_results = [r for r in state.search_results if r.iteration == iteration]
        
        # Fallback to most recent results if none match current iteration
        if not new_results:
            new_results = state.search_results[-15:]

        # Build rich results text with source metadata
        results_text = "\n\n".join([
            f"[{i+1}] Title: {r.title}\n     URL: {r.url}\n     Snippet: {r.snippet}"
            for i, r in enumerate(new_results[:15])
        ])

        # Build previous findings context
        previous_findings = ""
        if state.findings:
            previous_findings = "\n".join([
                f"- {f.topic} (confidence: {f.confidence:.0%}): {', '.join(f.key_facts[:3])}"
                for f in state.findings[-5:]
            ])

        # Previous knowledge gaps
        previous_gaps = ""
        if state.analysis_notes:
            previous_gaps = "\n".join([f"- {note}" for note in state.analysis_notes[-3:]])

        # Current task focus
        current_task = state.current_task or (
            state.research_plan[min(iteration, len(state.research_plan) - 1)]
            if state.research_plan else state.user_question
        )

        messages = [
            SystemMessage(content=DEEP_RESEARCH_PROMPTS["ANALYZE_SYSTEM"]),
            HumanMessage(content=ANALYZE_USER.format(
                user_question=state.user_question,
                current_task=current_task,
                search_results=results_text[:5000],
                previous_findings=previous_findings or "No previous findings",
                previous_gaps=previous_gaps or "No previous gaps identified",
            )),
        ]

        service_logger.info(f"Analyzing {len(new_results)} results for iteration {iteration + 1}, focus: '{current_task[:60]}'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(AnalysisResult)
        result = await llm_with_structure.ainvoke(messages)

        # Build the finding object
        finding = ResearchFinding(
            topic=current_task,
            key_facts=result.key_findings[:7],
            sources=[r.url for r in new_results[:5]],
            confidence=result.confidence,
        )

        # Log contradictions if any
        if result.contradictions:
            service_logger.warning(f"Contradictions detected: {result.contradictions}")

        service_logger.info(
            f"Analysis complete: {len(result.key_findings)} findings, "
            f"{len(result.knowledge_gaps)} gaps, confidence={result.confidence:.0%}, "
            f"evidence={result.evidence_strength}, contradictions={len(result.contradictions)}"
        )

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_analyze",
                "message": (
                    f"Extracted {len(result.key_findings)} key findings..."
                ),
            },
        )

        return {
            "findings": [f.model_dump() for f in state.findings + [finding]],
            "analysis_notes": state.analysis_notes + result.knowledge_gaps,
        }