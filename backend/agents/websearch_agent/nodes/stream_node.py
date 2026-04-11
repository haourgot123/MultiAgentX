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
                "message": "Synthesizing an answer from the search results...",
            },
        )

        # Handle empty search results gracefully
        if not state.search_results:
            dispatch_custom_event(
                "status",
                {
                    "step": "websearch_answer",
                    "message": "No search results found.",
                },
            )
            fallback_output = (
                "I searched the web but couldn't find relevant results for your query. "
                "This might be due to a network issue or the search terms not matching available content. "
                "Please try rephrasing your question or check your internet connection."
            )
            return {"output": fallback_output}

        # Build rich search context with metadata
        current_date = datetime.now().strftime("%Y-%m-%d")
        search_context = f"Search Results (retrieved on {current_date}):\n\n"
        for idx, res in enumerate(state.search_results):
            title = getattr(res, 'title', 'Untitled')
            snippet = getattr(res, 'snippet', 'No description available')
            url = getattr(res, 'url', '')
            search_context += (
                f"[{idx+1}] Title: {title}\n"
                f"    URL: {url}\n"
                f"    Content: {snippet}\n\n"
            )

        user_prompt = (
            f"User Question: {state.user_question}\n\n"
            f"{search_context}\n"
            f"Using the {len(state.search_results)} search results above, provide a comprehensive, "
            f"well-cited answer to the user's question. Follow the citation format specified in your instructions."
        )

        # Inject current_date into system prompt
        system_prompt = WEBSEARCH_SYSTEM_MESSAGE.format(current_date=current_date)

        messages = [
            SystemMessage(content=system_prompt),
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
                "message": "Web search answer ready.",
            },
        )

        return {"output": full_output}