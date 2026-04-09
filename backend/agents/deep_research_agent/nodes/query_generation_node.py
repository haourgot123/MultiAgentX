from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="deep-research-query")


class SearchQueries(BaseModel):
    queries: List[str] = Field(description="list of search queries")


QUERY_GEN_SYSTEM = """You are an expert search query generator. Create effective search queries to find relevant information.

Guidelines:
1. Generate 2-3 focused search queries
2. Use specific keywords and phrases
3. Consider different search angles
4. Keep queries concise and targeted
5. Consider what information is still needed based on previous findings"""


QUERY_GEN_USER = """Generate search queries for this research step:

Research Plan: {research_plan}
Current Iteration: {current_iteration}/{max_iterations}
Previous Findings: {findings_summary}
Knowledge Gaps: {knowledge_gaps}

Main Question: {user_question}

Generate targeted search queries to fill knowledge gaps."""


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
                "message": f"🔍 Generating search queries (iteration {state.current_iteration + 1}/{state.max_iterations})...",
            },
        )

        findings_summary = ""
        if state.findings:
            findings_summary = "\n".join([
                f"- {f.topic}: {', '.join(f.key_facts[:3])}"
                for f in state.findings[-3:]
            ])

        knowledge_gaps = ""
        if state.current_iteration > 0 and state.analysis_notes:
            knowledge_gaps = "\n".join(state.analysis_notes[-2:])

        plan_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(state.research_plan)])

        messages = [
            SystemMessage(content=QUERY_GEN_SYSTEM),
            HumanMessage(content=QUERY_GEN_USER.format(
                research_plan=plan_str,
                current_iteration=state.current_iteration + 1,
                max_iterations=state.max_iterations,
                findings_summary=findings_summary or "No findings yet",
                knowledge_gaps=knowledge_gaps or "Starting initial research",
                user_question=state.user_question,
            )),
        ]

        service_logger.info(f"Generating search queries for iteration {state.current_iteration + 1}")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(SearchQueries)
        result = await llm_with_structure.ainvoke(messages)

        queries = result.queries[:3]
        service_logger.info(f"Generated {len(queries)} search queries")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_query_gen",
                "message": f"✅ Generated {len(queries)} search queries.",
            },
        )

        return{
            "search_queries": queries,
        }