from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.deep_research import DEEP_RESEARCH_PROMPTS


service_logger = logger.bind(service="deep-research-query")


class SearchQueries(BaseModel):
    queries: List[str] = Field(description="list of 2-3 focused search queries")


QUERY_GEN_USER = """Generate search queries for this research step:

Research Plan:
{research_plan}

Current Focus: Sub-question {current_focus_idx} — {current_focus}

Current Iteration: {current_iteration}/{max_iterations}

Previous Findings Summary:
{findings_summary}

Knowledge Gaps Identified:
{knowledge_gaps}

Previously Used Queries (DO NOT repeat these):
{previous_queries}

Main Question: {user_question}

Generate 2-3 targeted, unique search queries that:
1. Focus primarily on the current sub-question
2. Fill identified knowledge gaps
3. Are different from all previously used queries
4. Mix broad and specific approaches"""


class QueryGenerationNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_query_gen",
                "message": f"Generating search queries (iteration {state.current_iteration + 1}/{state.max_iterations})...",
            },
        )

        # Build findings summary from previous iterations
        findings_summary = ""
        if state.findings:
            findings_summary = "\n".join([
                f"- {f.topic}: {', '.join(f.key_facts[:3])}"
                for f in state.findings[-5:]
            ])

        # Extract knowledge gaps from analysis notes
        knowledge_gaps = ""
        if state.current_iteration > 0 and state.analysis_notes:
            knowledge_gaps = "\n".join(state.analysis_notes[-3:])

        # Build research plan display string
        plan_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(state.research_plan)])

        # Determine current focus sub-question based on iteration
        current_focus_idx = min(state.current_iteration, len(state.research_plan) - 1)
        current_focus = state.research_plan[current_focus_idx] if state.research_plan else state.user_question

        # Collect previously used queries for deduplication
        previous_queries = "\n".join([f"- {q}" for q in state.search_queries]) if state.search_queries else "None yet"

        messages = [
            SystemMessage(content=DEEP_RESEARCH_PROMPTS["QUERY_GEN_SYSTEM"]),
            HumanMessage(content=QUERY_GEN_USER.format(
                research_plan=plan_str,
                current_focus_idx=current_focus_idx + 1,
                current_focus=current_focus,
                current_iteration=state.current_iteration + 1,
                max_iterations=state.max_iterations,
                findings_summary=findings_summary or "No findings yet",
                knowledge_gaps=knowledge_gaps or "Starting initial research",
                previous_queries=previous_queries,
                user_question=state.user_question,
            )),
        ]

        service_logger.info(f"Generating search queries for iteration {state.current_iteration + 1}, focus: '{current_focus[:60]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(SearchQueries)
        result = await llm_with_structure.ainvoke(messages)

        # Deduplicate against all previously used queries
        existing_queries_lower = {q.strip().lower() for q in state.search_queries}
        new_queries = []
        for q in result.queries:
            q_clean = q.strip()
            if q_clean.lower() not in existing_queries_lower:
                new_queries.append(q_clean)
                existing_queries_lower.add(q_clean.lower())

        # Ensure we have at least 1 query; cap at 3
        queries = new_queries[:3]
        if not queries:
            # Fallback: use the current focus sub-question as a query
            service_logger.warning("All generated queries were duplicates, using focus sub-question as fallback")
            queries = [current_focus]

        service_logger.info(f"Generated {len(queries)} unique search queries (filtered from {len(result.queries)})")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_query_gen",
                "message": f"Generated {len(queries)} unique search queries ...",
            },
        )

        return {
            "search_queries": queries,
            "current_task": current_focus,
        }