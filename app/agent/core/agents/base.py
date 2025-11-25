"""
Base Agent Module

This module provides the abstract base class for all agents in the system.
Following the factory design pattern, each agent must implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    This class defines the interface that all concrete agent implementations must follow.
    It integrates with LangGraph for state management and workflow orchestration.
    """

    def __init__(
        self,
        name: str,
        description: str,
        llm: Any = None,
        tools: Optional[List[Any]] = None,
        **kwargs
    ):
        """
        Initialize the base agent.

        Args:
            name: Name of the agent
            description: Description of the agent's purpose
            llm: Language model instance (optional)
            tools: List of tools available to the agent (optional)
            **kwargs: Additional configuration parameters
        """
        self.name = name
        self.description = description
        self.llm = llm
        self.tools = tools or []
        self.config = kwargs
        self._graph: Optional[StateGraph] = None
        self._compiled_graph: Optional[Any] = None

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """
        Build the LangGraph StateGraph for this agent.

        Returns:
            StateGraph: The constructed state graph
        """
        pass

    @abstractmethod
    def get_state_schema(self) -> type:
        """
        Get the state schema class for this agent.

        Returns:
            type: The state schema class (TypedDict)
        """
        pass

    def compile(self) -> Any:
        """
        Compile the agent's graph for execution.

        Returns:
            Compiled graph ready for invocation
        """
        if self._compiled_graph is None:
            self._graph = self.build_graph()
            self._compiled_graph = self._graph.compile()
        return self._compiled_graph

    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously invoke the agent with input data.

        Args:
            input_data: Input data dictionary matching the state schema

        Returns:
            Output data dictionary from the agent execution
        """
        compiled_graph = self.compile()
        result = await compiled_graph.ainvoke(input_data)
        return result

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronously invoke the agent with input data.

        Args:
            input_data: Input data dictionary matching the state schema

        Returns:
            Output data dictionary from the agent execution
        """
        compiled_graph = self.compile()
        result = compiled_graph.invoke(input_data)
        return result

    async def astream(self, input_data: Dict[str, Any]):
        """
        Stream agent execution results asynchronously.

        Args:
            input_data: Input data dictionary matching the state schema

        Yields:
            Intermediate states during execution
        """
        compiled_graph = self.compile()
        async for chunk in compiled_graph.astream(input_data):
            yield chunk

    def stream(self, input_data: Dict[str, Any]):
        """
        Stream agent execution results synchronously.

        Args:
            input_data: Input data dictionary matching the state schema

        Yields:
            Intermediate states during execution
        """
        compiled_graph = self.compile()
        for chunk in compiled_graph.stream(input_data):
            yield chunk

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.

        Returns:
            Dictionary containing agent metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "tools": [tool.name if hasattr(tool, "name") else str(tool) for tool in self.tools],
            "config": self.config
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
