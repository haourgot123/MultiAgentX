from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="deep-research-plan")


class ResearchPlan(BaseModel):
    sub_questions: List[str] = Field(description="list of research sub-questions")
    approach: str = Field(description="recommended research approach")


PLAN_SYSTEM = """You are an expert research planner. Your task is to create a structured research plan for complex questions.

Guidelines:
1. Break down complex questions into 3-5 focused sub-questions
2. Each sub-question should target a specific aspect
3. Consider different perspectives and dimensions
4. Order sub-questions logically (foundational → detailed)
5. Identify key information sources needed

Create actionable research questions that can be answered through web search."""


PLAN_USER = """Create a research plan for this question:

User Question: {user_question}

Previous Context: {context}

Generate 3-5 focused sub-questions to investigate this topic thoroughly."""


class PlanNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_plan",
                "message": "📋 Creating research plan...",
            },
        )

        context = ""
        if state.memories:
            recent_messages = state.memories[-3:] if len(state.memories) > 3 else state.memories
            context = "\n".join([
                f"{'User' if getattr(msg, 'role', '') == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:200]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=PLAN_SYSTEM),
            HumanMessage(content=PLAN_USER.format(
                user_question=state.user_question,
                context=context[:500] if context else "No previous context",
            )),
        ]

        service_logger.info(f"Creating research plan for: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(ResearchPlan)
        result = await llm_with_structure.ainvoke(messages)

        service_logger.info(f"Research plan created with {len(result.sub_questions)} sub-questions")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_plan",
                "message": f"✅ Research plan created: {len(result.sub_questions)} sub-questions to investigate.",
            },
        )

        # Emit plan_request event for human approval
        dispatch_custom_event(
            "plan_request",
            {
                "step": "deep_research_plan_approval",
                "plan": result.sub_questions,
                "message": "Research plan created. Awaiting user approval.",
            },
        )

        return {
            "research_plan": result.sub_questions,
        }