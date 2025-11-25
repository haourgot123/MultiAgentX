"""
Agent State Schemas Module

This module defines state schemas for different agent types.
States are used by LangGraph to manage agent execution flow.
"""

from typing import TypedDict, List, Optional, Any, Annotated, Dict
from langchain_core.messages import BaseMessage
import operator


class BaseAgentState(TypedDict):
    """
    Base state schema for all agents.

    This defines the minimal state structure that all agents should support.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    """List of messages in the conversation"""


class AnswerGenerationState(BaseAgentState):
    """
    State schema for answer generation agent.

    Extends BaseAgentState with fields specific to answer generation tasks.
    """
    question: str
    """The user's question"""

    context: Optional[str]
    """Retrieved context from knowledge base"""

    answer: Optional[str]
    """Generated answer"""

    sources: Optional[List[Dict[str, Any]]]
    """Source documents used for answer generation"""

    conversation_id: Optional[str]
    """Unique identifier for the conversation"""

    metadata: Optional[Dict[str, Any]]
    """Additional metadata"""


class ResearchAgentState(BaseAgentState):
    """
    State schema for research agent.

    Used for agents that perform multi-step research tasks.
    """
    query: str
    """Research query"""

    research_plan: Optional[List[str]]
    """Steps in the research plan"""

    findings: Optional[List[Dict[str, Any]]]
    """Research findings"""

    final_report: Optional[str]
    """Final research report"""

    iteration_count: int
    """Current iteration number"""

    max_iterations: int
    """Maximum allowed iterations"""


class ToolExecutionState(BaseAgentState):
    """
    State schema for agents that execute tools.

    Tracks tool execution and results.
    """
    tool_name: Optional[str]
    """Name of the tool to execute"""

    tool_input: Optional[Dict[str, Any]]
    """Input parameters for the tool"""

    tool_output: Optional[Any]
    """Output from tool execution"""

    tool_error: Optional[str]
    """Error message if tool execution failed"""

    should_continue: bool
    """Whether to continue execution"""


class DocumentProcessingState(BaseAgentState):
    """
    State schema for document processing agents.

    Used for agents that process and analyze documents.
    """
    document_ids: List[str]
    """List of document IDs to process"""

    processed_documents: Optional[List[Dict[str, Any]]]
    """Processed document data"""

    extraction_results: Optional[Dict[str, Any]]
    """Results from information extraction"""

    processing_status: str
    """Current processing status"""


class ConversationState(BaseAgentState):
    """
    State schema for conversational agents.

    Maintains conversation history and context.
    """
    user_id: Optional[str]
    """User identifier"""

    session_id: Optional[str]
    """Session identifier"""

    chat_history: List[Dict[str, str]]
    """Formatted chat history"""

    current_intent: Optional[str]
    """Detected user intent"""

    context_summary: Optional[str]
    """Summary of conversation context"""

    preferences: Optional[Dict[str, Any]]
    """User preferences"""


# Factory function to get state schema by name
def get_state_schema(schema_name: str) -> type:
    """
    Get a state schema class by name.

    Args:
        schema_name: Name of the state schema

    Returns:
        State schema class

    Raises:
        ValueError: If schema name is not recognized
    """
    schemas = {
        "base": BaseAgentState,
        "answer_generation": AnswerGenerationState,
        "research": ResearchAgentState,
        "tool_execution": ToolExecutionState,
        "document_processing": DocumentProcessingState,
        "conversation": ConversationState,
    }

    if schema_name not in schemas:
        raise ValueError(f"Unknown state schema: {schema_name}. Available: {list(schemas.keys())}")

    return schemas[schema_name]
