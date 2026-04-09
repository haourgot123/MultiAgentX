from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.websearch_agent.state import WebsearchAgentState
from backend.agents.prompts.transform_query import (
    TRANSFORM_QUERY_SYSTEM_MESSAGE,
    TRANSFORM_QUERY_USER_MESSAGE,
)


class TransformQueryResponse(BaseModel):
    transformed_queries: List[str] = Field(
        default_factory=list, description="Transformed queries"
    )


class TransformQueryNode(Runnable):
    def __init__(self) -> None:
        """
        Initialize the TransformQueryNode with a list of nodes
        """
        super().__init__()

    def invoke(self, state: WebsearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: WebsearchAgentState, config: dict = None, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "websearch_transform",
                "message": "🧠 Understanding intent and optimizing search queries...",
            },
        )

        messages = [
            SystemMessage(content=TRANSFORM_QUERY_SYSTEM_MESSAGE),
            *state.memories,
            HumanMessage(
                content=TRANSFORM_QUERY_USER_MESSAGE.format(
                    user_question=state.user_question
                )
            ),
        ]

        llm_with_structured_output = azure_chat_openai_gpt_5_1.with_structured_output(
            TransformQueryResponse
        )
        response = await llm_with_structured_output.ainvoke(messages)

        transformed_queries = response.transformed_queries

        dispatch_custom_event(
            "status",
            {
                "step": "websearch_transform",
                "message": f"🎯 Generated {len(transformed_queries)} optimized search queries.",
            },
        )

        return {"transformed_queries": transformed_queries}
