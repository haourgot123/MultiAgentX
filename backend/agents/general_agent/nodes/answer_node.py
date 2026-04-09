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

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        system_prompt = DIRECT_ANSWER_SYSTEM_MESSAGE.format(time_now=state.time_now)
        
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
        async for chunk in llm_with_config.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            full_output += content

        return {
            "output": full_output
        }
