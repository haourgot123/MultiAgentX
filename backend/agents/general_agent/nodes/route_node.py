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
        description="The exact route to take: 'websearch_agent', 'direct_response', 'deep_research_agent', or 'image_generation_agent'"
    )
    confidence: float = Field(
        default=0.9,
        description="Confidence level 0.0-1.0 for this routing decision"
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for why this route was selected"
    )
    detected_language: str = Field(
        default="auto",
        description="Detected language of the user question: 'vi', 'en', or 'auto'"
    )

VALID_ROUTES = {"websearch_agent", "direct_response", "deep_research_agent", "image_generation_agent"}

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
            {"step": "routing", "message": "Analyzing the request and selecting the best route..."},
        )

        system_prompt = ROUTE_SYSTEM_MESSAGE.format(
            is_web_search_enabled=state.is_web_search_enabled,
            is_deep_research_enabled=state.is_deep_research_enabled,
            is_generate_image_enabled=state.is_generate_image_enabled,
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
        confidence = response.confidence
        reasoning = response.reasoning
        
        # Validate route — fallback to direct_response if invalid
        if route not in VALID_ROUTES:
            logger.warning(f"RouteNode returned invalid route '{route}', falling back to direct_response")
            route = "direct_response"
            confidence = 0.5
        
        # Enforce feature flag constraints
        if route == "websearch_agent" and not state.is_web_search_enabled:
            logger.info("Websearch requested but disabled, falling back to direct_response")
            route = "direct_response"
        elif route == "deep_research_agent" and not state.is_deep_research_enabled:
            logger.info("Deep research requested but disabled, falling back to direct_response")
            route = "direct_response"
        elif route == "image_generation_agent" and not state.is_generate_image_enabled:
            logger.info("Image generation requested but disabled, falling back to direct_response")
            route = "direct_response"
        
        # Low confidence fallback
        if confidence < 0.4 and route != "direct_response":
            logger.info(f"RouteNode confidence too low ({confidence:.2f}), falling back to direct_response")
            route = "direct_response"
        
        logger.info(f"RouteNode decided route: {route} (confidence: {confidence:.2f}, reason: {reasoning[:100]})")
        dispatch_custom_event(
            "status",
            {
                "step": "routing",
                "message": f"Route selected: `{route}` (confidence: {confidence:.0%})",
            },
        )
        
        return {
            "route": route
        }