from typing import List
from datetime import datetime

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.general_agent.state import Tag
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.websearch_agent.state import WebsearchAgentState
from backend.agents.prompts.websearch import WEBSEARCH_SYSTEM_MESSAGE


class StreamNode(Runnable):
    def __init__(self) -> None:
        """
        Final websearch node that synthesizes an answer from search_results
        and streams tokens via the outer graph.
        """
        super().__init__()

    def invoke(self, state: WebsearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: WebsearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "websearch_answer",
                "message": "🧩 Synthesizing an answer from the search results...",
            },
        )

        # Build search context
        search_context = "Search Results:\n"
        for idx, res in enumerate(state.search_results):
            search_context += (
                f"[{idx+1}] Title: {getattr(res, 'title', '')}\n"
                f"Snippet: {getattr(res, 'snippet', '')}\n"
                f"Link: {getattr(res, 'url', '')}\n\n"
            )

        user_prompt = (
            f"Question: {state.user_question}\n\n"
            f"{search_context}\n"
            "Use the search results above to answer the question as accurately as possible."
        )

        messages = [
            SystemMessage(content=WEBSEARCH_SYSTEM_MESSAGE),
            *state.memories,
            HumanMessage(content=user_prompt),
        ]

        llm_with_config = azure_chat_openai_gpt_5_1.with_config(
            {"tags": [Tag.streaming_node.name]}
        )

        full_output = ""
        async for chunk in llm_with_config.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            full_output += content

        dispatch_custom_event(
            "status",
            {
                "step": "websearch_answer",
                "message": "✅ Web search answer ready.",
            },
        )

        return {"output": full_output}