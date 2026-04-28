import inspect

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger
from backend.agents.general_agent.state import GeneralAgentState, Tag
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.answering import (
    DIRECT_ANSWER_SYSTEM_MESSAGE,
    DIRECT_ANSWER_USER_MESSAGE,
)

class AnswerNode(Runnable):
    def __init__(self) -> None:
        """
        Initialize the AnswerNode.
        """
        super().__init__()

    def invoke(self, state: GeneralAgentState, **kwargs):
        pass

    @staticmethod
    async def _iter_stream_chunks(stream):
        if hasattr(stream, "__aiter__"):
            iterator = stream.__aiter__()
            if inspect.isawaitable(iterator):
                iterator = await iterator

            if hasattr(iterator, "__anext__"):
                while True:
                    try:
                        yield await iterator.__anext__()
                    except StopAsyncIteration:
                        break
                return

            for chunk in iterator:
                yield chunk
            return

        for chunk in stream:
            yield chunk

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        # Build the system prompt with time and long-term memory context
        long_term_ctx = state.long_term_memory_context or "No long-term memories available."
        
        system_prompt = DIRECT_ANSWER_SYSTEM_MESSAGE.format(
            time_now=state.time_now,
            long_term_memory_context=long_term_ctx,
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            *state.memories,
            HumanMessage(
                content=DIRECT_ANSWER_USER_MESSAGE.format(
                    user_question=state.user_question
                )
            ),
        ]
        
        logger.info(f"AnswerNode processing direct response for question: '{state.user_question}'")
        if long_term_ctx and long_term_ctx != "No long-term memories available.":
            logger.info(f"AnswerNode using long-term memory context ({len(long_term_ctx)} chars)")
        
        # Attach streaming tag so outer graph can capture on_chat_model_stream events
        config = kwargs.get("config", {}) or {}
        existing_tags = config.get("tags", [])
        if isinstance(existing_tags, list):
            config["tags"] = list(set(existing_tags + [Tag.streaming_node.name]))
        else:
            config["tags"] = [Tag.streaming_node.name]

        # Stream tokens from the LLM while accumulating the final output
        full_output = ""
        llm_with_config = azure_chat_openai_gpt_5_1.with_config(config)
        stream = llm_with_config.astream(messages)
        if inspect.isawaitable(stream):
            stream = await stream
        async for chunk in self._iter_stream_chunks(stream):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            full_output += content

        return {
            "output": full_output
        }
