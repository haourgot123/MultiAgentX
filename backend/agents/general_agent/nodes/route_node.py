from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger
from backend.agents.general_agent.state import GeneralAgentState, Node, Tag
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.routing import (
    ROUTE_SYSTEM_MESSAGE,
    ROUTE_USER_MESSAGE,
)

class RouteResponse(BaseModel):
    route: str = Field(
        description="The exact route to take: 'websearch_agent', 'direct_response', etc."
    )

class RouteNode(Runnable):
    def __init__(self) -> None:
        """
        Initialize the RouteNode.
        """
        super().__init__()

    def invoke(self, state: GeneralAgentState, **kwargs):
        pass

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {"step": "routing", "message": "🧭 Analyzing the request and selecting the best route..."},
        )

        system_prompt = ROUTE_SYSTEM_MESSAGE.format(
            is_web_search_enabled=state.is_web_search_enabled,
            is_deep_research_enabled=state.is_deep_research_enabled,
            is_generate_image_enabled=state.is_generate_image_enabled,
            is_rag_enabled=state.is_rag_enabled or len(state.file_ids) > 0,
        )

        messages = [
            SystemMessage(content=system_prompt),
            *state.memories,
            HumanMessage(
                content=ROUTE_USER_MESSAGE.format(user_question=state.user_question)
            ),
        ]
        
        logger.info(f"RouteNode evaluating question: '{state.user_question}'")
        
        # Use structured output to guarantee adherence to the exact route strings
        llm_with_structured_output = azure_chat_openai_gpt_5_1.with_structured_output(RouteResponse)
        response = await llm_with_structured_output.ainvoke(messages)
        route = response.route
        
        logger.info(f"RouteNode decided route: {route}")
        dispatch_custom_event(
            "status",
            {
                "step": "routing",
                "message": f"✅ Route selected: `{route}`.",
            },
        )
        
        return {
            "route": route
        }