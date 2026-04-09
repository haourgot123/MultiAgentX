from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState, SearchResult, ResearchFinding
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="deep-research-analyze")


class AnalysisResult(BaseModel):
    key_findings: List[str] = Field(description="key facts and insights extracted")
    knowledge_gaps: List[str] = Field(description="areas needing more research")
    confidence: float = Field(description="confidence level 0-1")


ANALYZE_SYSTEM = """You are a research analyst. Analyze search results to extract key findings and identify knowledge gaps.

Guidelines:
1. Extract key facts and insights from the search results
2. Identify areas where more information is needed
3. Assess confidence in the findings
4. Note any contradictions or inconsistencies
5. Consider credibility and recency of sources"""


ANALYZE_USER = """Analyze these search results for the research question:

Main Question: {user_question}

Search Results:
{search_results}

Previous Findings: {previous_findings}

Extract key findings and identify knowledge gaps."""


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
                "message": "🔬 Analyzing findings...",
            },
        )

        iteration = state.current_iteration
        
        new_results = [r for r in state.search_results if r.iteration == iteration]
        
        if not new_results:
            new_results = state.search_results[-10:]

        results_text = "\n\n".join([
            f"[{i+1}] {r.title}\nURL: {r.url}\nSnippet: {r.snippet}"
            for i, r in enumerate(new_results[:10])
        ])

        previous_findings = ""
        if state.findings:
            previous_findings = "\n".join([
                f"- {f.topic}: {', '.join(f.key_facts[:2])}"
                for f in state.findings[-3:]
            ])

        messages = [
            SystemMessage(content=ANALYZE_SYSTEM),
            HumanMessage(content=ANALYZE_USER.format(
                user_question=state.user_question,
                search_results=results_text[:3000],
                previous_findings=previous_findings or "No previous findings",
            )),
        ]

        service_logger.info(f"Analyzing {len(new_results)} results for iteration {iteration + 1}")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(AnalysisResult)
        result = await llm_with_structure.ainvoke(messages)

        finding = ResearchFinding(
            topic=state.research_plan[min(iteration, len(state.research_plan) - 1)] if state.research_plan else state.user_question,
            key_facts=result.key_findings[:5],
            sources=[r.url for r in new_results[:3]],
            confidence=result.confidence,
        )

        service_logger.info(f"Analysis complete: {len(result.key_findings)} findings, {len(result.knowledge_gaps)} gaps")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_analyze",
                "message": f"✅ Extracted {len(result.key_findings)} key findings.",
            },
        )

        return {
            "findings": [f.model_dump() for f in state.findings + [finding]],
            "analysis_notes": state.analysis_notes + result.knowledge_gaps,
        }