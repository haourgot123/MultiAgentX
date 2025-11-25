from typing import Any, Dict, Optional, Type, List, Callable
import logging
from .base import BaseTool
from .tool import (
    SearchDefaultKnowledgeBaseTool,
    SearchCompanyKnowledgeBaseTool,
    SearchProjectKnowledgeBaseTool,
    SearchExperienceKnowledgeBaseTool,
    FillingExperienceTicketTool,
    TavilyWebSearchTool
)

logger = logging.getLogger(__name__)


class ToolFactory:
    """
    Factory for tool types.
    """
    
    _tools: Dict[str, Callable[..., BaseTool]] = {}  
    @classmethod
    def register(
        cls, 
        tool_name: str, 
        tool_class: Callable[..., BaseTool],
    ):
        cls._tools[tool_name] = tool_class
        logger.info(f"Registered tool: {tool_name} -> {tool_class.__name__}")
    @classmethod
    def create_tool(
        cls,
        tool_name: str,
        tool_params: Dict[str, Any] = None,
        **kwargs
    ) -> BaseTool:
        tool_class = cls._tools[tool_name]
        return tool_class(**(tool_params or {}), **kwargs)
 

ToolFactory.register("search_default_knowledge_base", SearchDefaultKnowledgeBaseTool)
ToolFactory.register("search_company_knowledge_base", SearchCompanyKnowledgeBaseTool)
ToolFactory.register("search_project_knowledge_base", SearchProjectKnowledgeBaseTool)
ToolFactory.register("search_experience_knowledge_base", SearchExperienceKnowledgeBaseTool)
ToolFactory.register("filling_experience_ticket", FillingExperienceTicketTool)
ToolFactory.register("tavily_search", TavilyWebSearchTool)