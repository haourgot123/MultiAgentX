from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import adispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, Tag
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.rag import RAG_PROMPTS




class SynthesizeNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "Synthesizing answer from documents...",
            },
        )

        context = state.combined_context

        if not context or not context.strip():
            logger.warning("[RAGAgent (SynthesizeNode)] No context to synthesize — returning no-context response")
            await adispatch_custom_event(
                "status",
                {
                    "step": "rag_synthesize",
                    "message": "No relevant documents found.",
                },
            )
            return {
                "final_answer": RAG_PROMPTS["NO_CONTEXT_RESPONSE"],
            }

        # Count unique files from citation_map
        unique_files = set()
        for label, data in state.citation_map.items():
            if isinstance(data, dict):
                unique_files.add(data.get("file_name", "unknown"))

        logger.info(
            f"[RAGAgent (SynthesizeNode)] Synthesizing from context ({len(context)} chars) across {len(unique_files)} file(s)"
        )

        messages = [
            SystemMessage(content=RAG_PROMPTS["SYNTHESIZE_SYSTEM"]),
            HumanMessage(content=RAG_PROMPTS["SYNTHESIZE_USER"].format(
                user_question=state.user_question,
                context=context[:12000],
            )),
        ]

        # Stream tokens natively using tagged config so the outer graph's
        # astream_events captures on_chat_model_stream events in real-time
        llm_with_config = azure_chat_openai_gpt_5_1.with_config(
            {"tags": [Tag.streaming_node.name]}
        )

        final_answer = ""
        async for chunk in llm_with_config.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            final_answer += content

        logger.info(
            f"[RAGAgent (SynthesizeNode)] Synthesized answer of {len(final_answer)} characters from {len(unique_files)} files"
        )

        return {
            "final_answer": final_answer,
        }