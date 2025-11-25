"""
Answer Generation Agent Module

This module implements a RAG (Retrieval-Augmented Generation) agent
for answering questions based on retrieved context.
"""

from typing import Any, Dict, Optional, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from .base import BaseAgent
from .components.states import AnswerGenerationState
from .components.nodes import AgentNodes


class AnswerGenerationAgent(BaseAgent):
    """
    Agent for generating answers to questions using RAG.

    This agent:
    1. Retrieves relevant context from a knowledge base
    2. Generates an answer using an LLM with the retrieved context
    3. Returns the answer with sources
    """

    def __init__(
        self,
        name: str = "AnswerGenerationAgent",
        description: str = "Agent for answering questions using retrieval-augmented generation",
        llm: Any = None,
        retriever: Any = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Answer Generation Agent.

        Args:
            name: Name of the agent
            description: Description of the agent
            llm: Language model instance
            retriever: Document retriever instance
            system_prompt: Custom system prompt for answer generation
            **kwargs: Additional configuration
        """
        super().__init__(name=name, description=description, llm=llm, **kwargs)
        self.retriever = retriever
        self.system_prompt = system_prompt or self._get_default_system_prompt()

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for answer generation."""
        return """You are a helpful AI assistant specialized in industrial maintenance and equipment troubleshooting.

Your task is to answer questions based on the provided context from technical manuals and documentation.

Guidelines:
- Answer questions accurately based on the provided context
- If the context doesn't contain enough information, clearly state this
- Be concise but comprehensive in your answers
- Reference specific sections or pages from the source documents when applicable
- Use technical terminology correctly
- If asked about safety procedures, emphasize the importance of following manufacturer guidelines

Always prioritize accuracy and safety in your responses."""

    def get_state_schema(self) -> type:
        """Get the state schema for this agent."""
        return AnswerGenerationState

    def build_graph(self) -> StateGraph:
        """
        Build the LangGraph for answer generation.

        The graph follows this flow:
        1. Start -> Retrieve relevant documents
        2. Retrieve -> Generate answer using LLM
        3. Generate -> End
        """
        # Create state graph
        graph = StateGraph(AnswerGenerationState)

        # Define nodes
        if self.retriever:
            graph.add_node("retrieve", AgentNodes.create_retrieval_node(self.retriever))
        else:
            # If no retriever, use a pass-through node
            graph.add_node("retrieve", lambda state: {"context": ""})

        graph.add_node(
            "generate",
            AgentNodes.create_answer_generation_node(
                llm=self.llm,
                prompt_template=self._get_prompt_template()
            )
        )

        # Define edges
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)

        return graph

    def _get_prompt_template(self) -> str:
        """Get the prompt template for answer generation."""
        return f"""{self.system_prompt}

Context from technical documentation:
{{context}}

Question: {{question}}

Answer:"""

    async def answer_question(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            question: The question to answer
            conversation_id: Optional conversation ID for tracking
            metadata: Optional additional metadata

        Returns:
            Dictionary containing answer, sources, and metadata
        """
        # Prepare input state
        input_state = {
            "question": question,
            "messages": [HumanMessage(content=question)],
            "conversation_id": conversation_id,
            "metadata": metadata or {},
            "context": None,
            "answer": None,
            "sources": None,
        }

        # Invoke agent
        result = await self.ainvoke(input_state)

        # Format response
        return {
            "answer": result.get("answer"),
            "sources": result.get("sources", []),
            "question": question,
            "conversation_id": conversation_id,
            "metadata": result.get("metadata", {}),
        }

    def answer_question_sync(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of answer_question.

        Args:
            question: The question to answer
            conversation_id: Optional conversation ID for tracking
            metadata: Optional additional metadata

        Returns:
            Dictionary containing answer, sources, and metadata
        """
        # Prepare input state
        input_state = {
            "question": question,
            "messages": [HumanMessage(content=question)],
            "conversation_id": conversation_id,
            "metadata": metadata or {},
            "context": None,
            "answer": None,
            "sources": None,
        }

        # Invoke agent
        result = self.invoke(input_state)

        # Format response
        return {
            "answer": result.get("answer"),
            "sources": result.get("sources", []),
            "question": question,
            "conversation_id": conversation_id,
            "metadata": result.get("metadata", {}),
        }

    async def astream_answer(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Stream the answer generation process.

        Args:
            question: The question to answer
            conversation_id: Optional conversation ID for tracking
            metadata: Optional additional metadata

        Yields:
            Intermediate states during execution
        """
        # Prepare input state
        input_state = {
            "question": question,
            "messages": [HumanMessage(content=question)],
            "conversation_id": conversation_id,
            "metadata": metadata or {},
            "context": None,
            "answer": None,
            "sources": None,
        }

        # Stream execution
        async for state in self.astream(input_state):
            yield state
