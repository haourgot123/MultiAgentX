from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import adispatch_custom_event
from pydantic import BaseModel, Field
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.rag import RAG_PROMPTS




class EvaluationResult(BaseModel):
    is_relevant: bool = Field(
        description="Whether the retrieved context is relevant enough to answer the user's question"
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score from 0.0 to 1.0 indicating relevance strength"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the relevance assessment"
    )
    suggested_query_refinement: str = Field(
        default="",
        description="If not relevant, suggest how to refine the search query for better results"
    )


class EvaluationNode(Runnable):
    """
    Evaluates whether retrieved chunks are relevant to the user's question.

    Decision flow:
    - If relevant → proceed to SynthesizeNode
    - If NOT relevant AND retry_count < max_retries → re-transform query and retry
    - If NOT relevant AND retry_count >= max_retries → pass empty context to SynthesizeNode
    """

    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        current_retry = state.retry_count

        await adispatch_custom_event(
            "status",
            {
                "step": "rag_evaluation",
                "message": f"Evaluating relevance of retrieved passages ...",
            },
        )

        # If no context was retrieved, mark as not relevant
        if not state.combined_context or not state.combined_context.strip():
            logger.warning("[RAGAgent (EvaluationNode)] No context to evaluate — marking as not relevant")

            if current_retry >= state.max_retries:
                logger.info("[RAGAgent (EvaluationNode)] Max retries reached with no context — proceeding with empty context")
                return {
                    "is_relevant": False,
                    "retry_count": current_retry,
                    "combined_context": "",
                    "evaluation_feedback": "No relevant documents found after multiple search attempts.",
                }

            return {
                "is_relevant": False,
                "retry_count": current_retry + 1,
                "evaluation_feedback": "No documents were retrieved. Try broadening the search terms.",
            }

        # Use LLM to evaluate relevance
        messages = [
            SystemMessage(content=RAG_PROMPTS["EVALUATION_SYSTEM"]),
            HumanMessage(content=RAG_PROMPTS["EVALUATION_USER"].format(
                user_question=state.user_question,
                context=state.combined_context[:8000],
            )),
        ]

        try:
            llm_with_structure = azure_chat_openai_gpt_5_1.with_structured_output(EvaluationResult)
            result = await llm_with_structure.ainvoke(messages)

            logger.info(
                f"[RAGAgent (EvaluationNode)] Evaluation result: relevant={result.is_relevant}, "
                f"confidence={result.confidence:.2f}, "
                f"reasoning='{result.reasoning[:100]}'"
            )

            if result.is_relevant:
                await adispatch_custom_event(
                    "status",
                    {
                        "step": "rag_evaluation",
                        "message": f"Context is relevant. Generating answer...",
                    },
                )
                return {
                    "is_relevant": True,
                    "evaluation_feedback": result.reasoning,
                }

            # Not relevant — decide whether to retry
            if current_retry >= state.max_retries:
                logger.info(
                    f"[RAGAgent (EvaluationNode)] Max retries ({state.max_retries}) reached — proceeding with current context anyway"
                )
                await adispatch_custom_event(
                    "status",
                    {
                        "step": "rag_evaluation",
                        "message": "Max search attempts reached. Generating best-effort answer...",
                    },
                )
                # Keep the context we have — better than nothing after 3 attempts
                return {
                    "is_relevant": False,
                    "retry_count": current_retry,
                    "evaluation_feedback": result.reasoning,
                }

            # Not relevant and retries remaining — retry with refined query
            logger.info(
                f"[RAGAgent (EvaluationNode)] Context not relevant (attempt {current_retry + 1}/{state.max_retries}). "
                f"Suggestion: {result.suggested_query_refinement[:100]}"
            )
            await adispatch_custom_event(
                "status",
                {
                    "step": "rag_evaluation",
                    "message": f"Results not relevant enough. Refining search ...",
                },
            )
            return {
                "is_relevant": False,
                "retry_count": current_retry + 1,
                "evaluation_feedback": result.suggested_query_refinement or result.reasoning,
                # Clear retrieval state for next attempt
                "retrieved_chunks": [],
                "combined_context": "",
                "citation_map": {},
            }

        except Exception as e:
            logger.error(f"[RAGAgent (EvaluationNode)] Evaluation failed: {e}")
            # Graceful degradation: assume relevance and proceed

            return {
                "is_relevant": True,
                "evaluation_feedback": f"Evaluation skipped due to error: {str(e)[:100]}",
            }
