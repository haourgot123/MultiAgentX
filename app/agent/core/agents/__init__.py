"""
Agent Package

This package provides a flexible agent system following the Factory Design Pattern.
It includes base classes, concrete implementations, and factory utilities.
"""

from .base import BaseAgent
from .answer_generation_agent import AnswerGenerationAgent
from .factory import (
    AgentFactory,
    AgentRegistry,
    create_agent,
    register_agent,
    list_agent_types,
    get_agent_info,
    register_agent_type,
)
from .components.states import (
    BaseAgentState,
    AnswerGenerationState,
    ResearchAgentState,
    ToolExecutionState,
    DocumentProcessingState,
    ConversationState,
    get_state_schema,
)
from .components.nodes import (
    AgentNodes,
    should_continue_research,
    should_execute_tool,
    route_by_intent,
)

__all__ = [
    # Base classes
    "BaseAgent",
    # Concrete agents
    "AnswerGenerationAgent",
    # Factory and registry
    "AgentFactory",
    "AgentRegistry",
    "create_agent",
    "register_agent",
    "list_agent_types",
    "get_agent_info",
    "register_agent_type",
    # States
    "BaseAgentState",
    "AnswerGenerationState",
    "ResearchAgentState",
    "ToolExecutionState",
    "DocumentProcessingState",
    "ConversationState",
    "get_state_schema",
    # Nodes and utilities
    "AgentNodes",
    "should_continue_research",
    "should_execute_tool",
    "route_by_intent",
]
