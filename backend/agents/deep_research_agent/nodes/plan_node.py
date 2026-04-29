from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.deep_research import DEEP_RESEARCH_PROMPTS
from backend.agents.utils import astream_custom_event


class ResearchPlan(BaseModel):
    sub_questions: List[str] = Field(description="list of 3-5 research sub-questions")
    approach: str = Field(description="recommended research methodology: exploratory, comparative, analytical, predictive, or evaluative")
    priority_order: List[int] = Field(
        default_factory=list,
        description="priority order of sub-questions (1-indexed), most important first"
    )
    estimated_depth: str = Field(
        default="medium",
        description="estimated research depth needed: shallow (1 iteration), medium (2 iterations), deep (3 iterations)"
    )


PLAN_USER = """Create a comprehensive research plan for this question:

User Question: {user_question}

Previous Context: {context}

Instructions:
1. Analyze the question type (exploratory, comparative, analytical, predictive, evaluative)
2. Break it down into 3-5 focused, MECE sub-questions
3. Order sub-questions logically: foundational → analytical → forward-looking
4. Specify the recommended research approach
5. Prioritize sub-questions by importance
6. Estimate the depth of research needed"""


class PlanNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        # If plan already approved (coming from approve endpoint), skip re-planning
        if state.plan_approved and state.research_plan:
            logger.info(f"[DeepResearchAgent (PlanNode)] Skipping plan creation - plan already approved")
            await astream_custom_event(
                event_name="status",
                step="deep_research_plan",
                message="Using approved research plan...",
            )
            return {"research_plan": state.research_plan}

        await astream_custom_event(
            event_name="status",
            step="deep_research_plan",
            message="Creating research plan...",
        )   

        # Build conversation context from memories
        context = ""
        if state.memories:
            recent_messages = state.memories[-5:] if len(state.memories) > 5 else state.memories
            context = "\n".join([
                f"{'User' if getattr(msg, 'role', '') == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:300]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=DEEP_RESEARCH_PROMPTS["PLAN_SYSTEM"]),
            HumanMessage(content=PLAN_USER.format(
                user_question=state.user_question,
                context=context[:1000] if context else "No previous context",
            )),
        ]

        logger.info(f"[DeepResearchAgent (PlanNode)] Creating research plan for: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(ResearchPlan)
        result = await llm_with_structure.ainvoke(messages)

        # Validate sub-questions count (enforce 3-5 range)
        sub_questions = result.sub_questions
        if len(sub_questions) < 3:
            logger.warning(f"[DeepResearchAgent (PlanNode)] Plan generated only {len(sub_questions)} sub-questions, padding")
        elif len(sub_questions) > 5:
            logger.info(f"[DeepResearchAgent (PlanNode)] Plan generated {len(sub_questions)} sub-questions, trimming to 5")
            sub_questions = sub_questions[:5]

        logger.info(
            f"[DeepResearchAgent (PlanNode)] Research plan created: {len(sub_questions)} sub-questions, "
            f"approach={result.approach}, depth={result.estimated_depth}"
        )

        astream_custom_event(
            event_name="status",
            step="deep_research_plan_approval",
            message="Research plan created. Awaiting user approval.",
            plan=sub_questions,
        )

        return {
            "research_plan": sub_questions,
        }