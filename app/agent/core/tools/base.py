from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Base class for all tools.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the tool with the given input.
        """
        pass
    
    @abstractmethod
    async def ainvoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the tool with the given input asynchronously.
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this tool.
        """
        return {
            "name": self.name,
            "description": self.description
        }
    
    
