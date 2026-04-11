from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.rag import RAG_PROMPTS


service_logger = logger.bind(service="rag-query-transform")


class TransformedQuery(BaseModel):
    optimized_query: str = Field(description="optimized primary search query for document retrieval")
    keywords: list[str] = Field(default_factory=list, description="key terms extracted from the query")
    hypothetical_answer: str = Field(
        default="",
        description="a hypothetical 1-2 sentence answer that a document might contain (HyDE approach)"
    )
    expanded_query: str = Field(
        default="",
        description="an alternative query with synonyms and related terms for broader coverage"
    )


class QueryTransformNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_query_transform",
                "message": "Optimizing query for document search...",
            },
        )

        # Build conversation context from memories
        context = ""
        if state.memories:
            recent_messages = state.memories[-4:] if len(state.memories) > 4 else state.memories
            context = "\n".join([
                f"{'User' if msg.role == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:200]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=RAG_PROMPTS["QUERY_TRANSFORM_SYSTEM"]),
            HumanMessage(content=RAG_PROMPTS["QUERY_TRANSFORM_USER"].format(
                user_question=state.user_question,
                context=context[:1000] if context else "No previous context"
            )),
        ]

        service_logger.info(f"Transforming query: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(TransformedQuery)
        result = await llm_with_structure.ainvoke(messages)

        # Use the HyDE hypothetical answer as the primary query if available,
        # because it better matches document language rather than question language
        primary_query = result.optimized_query
        
        # Log all generated query variants
        service_logger.info(
            f"Transformed query: primary='{primary_query}', "
            f"keywords={result.keywords}, "
            f"hypothetical='{result.hypothetical_answer[:80]}...'"
        )

        dispatch_custom_event(
            "status",
            {
                "step": "rag_query_transform",
                "message": f"Optimized query: '{primary_query[:60]}...'",
            },
        )

        return {
            "transformed_query": primary_query,
        }