from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="rag-query-transform")


class TransformedQuery(BaseModel):
    optimized_query: str = Field(description="optimized search query for document retrieval")
    keywords: list[str] = Field(default_factory=list, description="key terms extracted from the query")


QUERY_TRANSFORM_SYSTEM = """You are a query optimization expert for document retrieval systems.
Your task is to transform user questions into optimized search queries that will retrieve the most relevant documents.

Guidelines:
1. Preserve the core intent of the question
2. Extract key terms and concepts
3. Remove filler words and irrelevant details
4. Add synonyms or related terms if helpful
5. Keep the query concise but comprehensive
6. Maintain any specific names, dates, or technical terms

Language: Respond in the same language as the user's question."""


QUERY_TRANSFORM_USER = """Transform this question into an optimized search query for document retrieval:

User Question: {user_question}

Conversation Context: {context}

Return an optimized query and extracted keywords."""


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
                "message": "🔄 Optimizing query for document search...",
            },
        )

        context = ""
        if state.memories:
            recent_messages = state.memories[-4:] if len(state.memories) > 4 else state.memories
            context = "\n".join([
                f"{'User' if msg.role == 'user' else 'Assistant'}: {getattr(msg, 'content', str(msg))[:200]}"
                for msg in recent_messages
            ])

        messages = [
            SystemMessage(content=QUERY_TRANSFORM_SYSTEM),
            HumanMessage(content=QUERY_TRANSFORM_USER.format(
                user_question=state.user_question,
                context=context[:1000] if context else "No previous context"
            )),
        ]

        service_logger.info(f"Transforming query: '{state.user_question[:100]}...'")

        llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(TransformedQuery)
        result = await llm_with_structure.ainvoke(messages)

        service_logger.info(f"Transformed query: '{result.optimized_query}'")

        dispatch_custom_event(
            "status",
            {
                "step": "rag_query_transform",
                "message": f"✅ Optimized query: '{result.optimized_query[:50]}...'",
            },
        )

        return {
            "transformed_query": result.optimized_query,
        }