"""
Agent Factory Module

This module implements the Factory Design Pattern for creating agents.
It provides a centralized registry and factory for all agent types.
"""

from typing import Any, Dict, Optional, Type, List, Callable
import logging

from .base import BaseAgent
from .answer_generation_agent import AnswerGenerationAgent


logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for agent types.

    This class maintains a mapping of agent names to their implementation classes.
    It follows the Registry pattern to enable dynamic agent creation.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._agent_configs: Dict[str, Dict[str, Any]] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register default built-in agents."""
        self.register("answer_generation", AnswerGenerationAgent)

    def register(
        self,
        agent_type: str,
        agent_class: Type[BaseAgent],
        default_config: Optional[Dict[str, Any]] = None
    ):
        """
        Register a new agent type.

        Args:
            agent_type: Unique identifier for the agent type
            agent_class: Agent class (must inherit from BaseAgent)
            default_config: Optional default configuration for this agent type

        Raises:
            TypeError: If agent_class doesn't inherit from BaseAgent
            ValueError: If agent_type is already registered
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class must inherit from BaseAgent, got {agent_class}")

        if agent_type in self._agents:
            logger.warning(f"Agent type '{agent_type}' is already registered. Overwriting.")

        self._agents[agent_type] = agent_class
        self._agent_configs[agent_type] = default_config or {}

        logger.info(f"Registered agent type: {agent_type} -> {agent_class.__name__}")

    def unregister(self, agent_type: str):
        """
        Unregister an agent type.

        Args:
            agent_type: Agent type to unregister

        Raises:
            KeyError: If agent_type is not registered
        """
        if agent_type not in self._agents:
            raise KeyError(f"Agent type '{agent_type}' is not registered")

        del self._agents[agent_type]
        if agent_type in self._agent_configs:
            del self._agent_configs[agent_type]

        logger.info(f"Unregistered agent type: {agent_type}")

    def get_agent_class(self, agent_type: str) -> Type[BaseAgent]:
        """
        Get the agent class for a given type.

        Args:
            agent_type: Agent type identifier

        Returns:
            Agent class

        Raises:
            KeyError: If agent_type is not registered
        """
        if agent_type not in self._agents:
            raise KeyError(
                f"Agent type '{agent_type}' is not registered. "
                f"Available types: {self.list_agent_types()}"
            )

        return self._agents[agent_type]

    def get_default_config(self, agent_type: str) -> Dict[str, Any]:
        """
        Get the default configuration for an agent type.

        Args:
            agent_type: Agent type identifier

        Returns:
            Default configuration dictionary
        """
        return self._agent_configs.get(agent_type, {}).copy()

    def list_agent_types(self) -> List[str]:
        """
        List all registered agent types.

        Returns:
            List of agent type identifiers
        """
        return list(self._agents.keys())

    def is_registered(self, agent_type: str) -> bool:
        """
        Check if an agent type is registered.

        Args:
            agent_type: Agent type identifier

        Returns:
            True if registered, False otherwise
        """
        return agent_type in self._agents


# Global registry instance
_global_registry = AgentRegistry()


class AgentFactory:
    """
    Factory for creating agent instances.

    This class implements the Factory Design Pattern, providing a unified
    interface for creating different types of agents.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize the agent factory.

        Args:
            registry: Optional custom agent registry. If None, uses global registry.
        """
        self.registry = registry or _global_registry

    def create_agent(
        self,
        agent_type: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            name: Optional custom name for the agent
            description: Optional custom description
            **kwargs: Additional configuration parameters

        Returns:
            Configured agent instance

        Raises:
            KeyError: If agent_type is not registered
            TypeError: If there's an error instantiating the agent
        """
        # Get agent class
        agent_class = self.registry.get_agent_class(agent_type)

        # Get default config and merge with provided kwargs
        config = self.registry.get_default_config(agent_type)
        config.update(kwargs)

        # Override name and description if provided
        if name:
            config["name"] = name
        if description:
            config["description"] = description

        # Create agent instance
        try:
            agent = agent_class(**config)
            logger.info(f"Created agent: {agent.name} (type: {agent_type})")
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent of type '{agent_type}': {e}")
            raise TypeError(f"Failed to create agent of type '{agent_type}': {e}") from e

    def create_agent_with_defaults(self, agent_type: str) -> BaseAgent:
        """
        Create an agent with default configuration.

        Args:
            agent_type: Type of agent to create

        Returns:
            Agent instance with default configuration
        """
        return self.create_agent(agent_type)

    def list_available_agents(self) -> List[str]:
        """
        List all available agent types.

        Returns:
            List of registered agent type identifiers
        """
        return self.registry.list_agent_types()

    def get_agent_info(self, agent_type: str) -> Dict[str, Any]:
        """
        Get information about an agent type.

        Args:
            agent_type: Agent type identifier

        Returns:
            Dictionary with agent type information
        """
        agent_class = self.registry.get_agent_class(agent_type)
        default_config = self.registry.get_default_config(agent_type)

        return {
            "agent_type": agent_type,
            "class_name": agent_class.__name__,
            "module": agent_class.__module__,
            "default_config": default_config,
            "docstring": agent_class.__doc__,
        }


# Convenience functions for global factory
def register_agent(
    agent_type: str,
    agent_class: Type[BaseAgent],
    default_config: Optional[Dict[str, Any]] = None
):
    """
    Register an agent type in the global registry.

    Args:
        agent_type: Unique identifier for the agent type
        agent_class: Agent class (must inherit from BaseAgent)
        default_config: Optional default configuration
    """
    _global_registry.register(agent_type, agent_class, default_config)


def create_agent(agent_type: str, **kwargs) -> BaseAgent:
    """
    Create an agent using the global factory.

    Args:
        agent_type: Type of agent to create
        **kwargs: Configuration parameters

    Returns:
        Configured agent instance
    """
    factory = AgentFactory()
    return factory.create_agent(agent_type, **kwargs)


def list_agent_types() -> List[str]:
    """
    List all available agent types from global registry.

    Returns:
        List of agent type identifiers
    """
    return _global_registry.list_agent_types()


def get_agent_info(agent_type: str) -> Dict[str, Any]:
    """
    Get information about an agent type from global registry.

    Args:
        agent_type: Agent type identifier

    Returns:
        Dictionary with agent information
    """
    factory = AgentFactory()
    return factory.get_agent_info(agent_type)


# Decorator for registering agents
def register_agent_type(
    agent_type: str,
    default_config: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator for registering agent classes.

    Usage:
        @register_agent_type("my_agent", {"param": "value"})
        class MyAgent(BaseAgent):
            ...

    Args:
        agent_type: Unique identifier for the agent type
        default_config: Optional default configuration

    Returns:
        Decorator function
    """
    def decorator(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        register_agent(agent_type, agent_class, default_config)
        return agent_class

    return decorator
