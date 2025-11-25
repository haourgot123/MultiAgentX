from .base import BaseTool
from loguru import logger
import urllib.parse
from typing import List, Literal, Dict, Any
from app.config.settings import _settings
from app.agent.utils.tools_helper.model import RetrieverModel, RetrieverModelResponse
from app.agent.utils.tools_helper.retriver import Retriever
from app.agent.utils.tools_helper.s3 import S3Service
from langchain_core.tools import Tool, StructuredTool
from app.agent.utils.tools_helper.web_search import TavilyWebSearch
from app.databases.sqldb_factory import SQLDBFactory
from app.agent.utils.tools_helper.format_response import( 
    format_text_response, 
    format_table_response, 
    format_image_response, 
    format_experience_response, 
    format_web_search_response,
    format_authen_check_response
)
from .tool_description import (
    search_default_knowledge_base_description,
    search_company_knowledge_base_description,
    search_project_knowledge_base_description,
    search_experience_knowledge_base_description,
    filling_experience_ticket_description,
    tavily_search_description,
    authen_check_description
)
from .tool_schema import (
    SearchDefaultKBSchema,
    SearchCompanyKBSchema,
    SearchProjectKBSchema,
    SearchExperienceKBSchema,
    FillingExperienceTicketSchema,
    TavilySearchSchema,
    AuthenCheckSchema
)


retriever = Retriever()
tavily_search = TavilyWebSearch()


class SearchDefaultKnowledgeBaseTool(BaseTool):
    """
    Tool for retrieving information from the knowledge base.
    """
    def __init__(self, kb_ids: List[str]):
        super().__init__(name="search_default_knowledge_base", description=search_default_knowledge_base_description)
        self.kb_ids = kb_ids
        self.tool = StructuredTool(
            name="search_default_knowledge_base",
            description=search_default_knowledge_base_description,
            func=self.invoke,
            coroutine=self.ainvoke,
            args_schema=SearchDefaultKBSchema
        )
    
    def invoke(
        self, 
        query: str,
        domain: Literal["fanuc", "mitsubishi"] = "fanuc",
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.default_collection,
                kb_ids=self.kb_ids,
                domain=domain,
                limit=_settings.qdrant.limit
            )
            response = retriever.invoke(input)
            return SearchDefaultKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching default knowledge base: {e}")
            return f"Error searching default knowledge base: {e}"
    async def ainvoke(
        self, 
        query: str,
        domain: Literal["fanuc", "mitsubishi"] = "fanuc",
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.default_collection,
                kb_ids=self.kb_ids,
                domain=domain,
                limit=_settings.qdrant.limit
            )
            response = await retriever.ainvoke(input)
            return SearchDefaultKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching default knowledge base: {e}")
            return f"Error searching default knowledge base: {e}"
    
    @staticmethod
    def format_response(response: RetrieverModelResponse) -> str:
        formatted_results = []
        for result in response.results:
            if result.get('document_type') == 'text':
                formatted_results.append(format_text_response(result))
            elif result.get('document_type') == 'table':
                formatted_results.append(format_table_response(result))
            elif result.get('document_type') == 'image':
                formatted_results.append(format_image_response(result))
        return "\n".join(formatted_results)

        
   
class SearchCompanyKnowledgeBaseTool(BaseTool):
    """
    Tool for retrieving information from the company knowledge base.
    """
    def __init__(self, kb_ids: List[str]):
        super().__init__(name="search_company_knowledge_base", description=search_company_knowledge_base_description)
        self.kb_ids = kb_ids
        self.tool = StructuredTool(
            name="search_company_knowledge_base",
            description=search_company_knowledge_base_description,
            func=self.invoke,
            coroutine=self.ainvoke,
            args_schema=SearchCompanyKBSchema
        )
    
    def invoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.company_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = retriever.invoke(input)
            return SearchCompanyKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching company knowledge base: {e}")
            return f"Error searching company knowledge base: {e}"
    async def ainvoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.company_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = await retriever.ainvoke(input)
            return SearchCompanyKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching company knowledge base: {e}")
            return f"Error searching company knowledge base: {e}"
    
    @staticmethod
    def format_response(response: RetrieverModelResponse) -> str:
        formatted_results = []
        for result in response.results:
            if result.get('document_type') == 'text':
                formatted_results.append(format_text_response(result))
            elif result.get('document_type') == 'table':
                formatted_results.append(format_table_response(result))
            elif result.get('document_type') == 'image':
                formatted_results.append(format_image_response(result))
        return "\n".join(formatted_results)
    

class SearchProjectKnowledgeBaseTool(BaseTool):
    """
    Tool for retrieving information from the project knowledge base.
    """
    def __init__(self, kb_ids: List[str]):
        super().__init__(name="search_project_knowledge_base", description=search_project_knowledge_base_description)
        self.kb_ids = kb_ids
        self.tool = StructuredTool(
            name="search_project_knowledge_base",
            description=search_project_knowledge_base_description,
            func=self.invoke,
            coroutine=self.ainvoke,
            args_schema=SearchProjectKBSchema
        )
    
    def invoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.project_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = retriever.invoke(input)
            return SearchProjectKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching project knowledge base: {e}")
            return f"Error searching project knowledge base: {e}"
    async def ainvoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,   
                collection_name=_settings.qdrant.project_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = await retriever.ainvoke(input)
            return SearchProjectKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching project knowledge base: {e}")
            return f"Error searching project knowledge base: {e}"
    
    @staticmethod
    def format_response(response: RetrieverModelResponse) -> str:
        formatted_results = []
        for result in response.results:
            if result.get('document_type') == 'text':
                formatted_results.append(format_text_response(result))
            elif result.get('document_type') == 'table':
                formatted_results.append(format_table_response(result))
            elif result.get('document_type') == 'image':
                formatted_results.append(format_image_response(result))
        return "\n".join(formatted_results)
    

class SearchExperienceKnowledgeBaseTool(BaseTool):
    """
    Tool for retrieving information from the experience knowledge base.
    """
    def __init__(self, kb_ids: List[str]):
        super().__init__(name="search_experience_knowledge_base", description=search_experience_knowledge_base_description)
        self.kb_ids = kb_ids
        self.tool = StructuredTool(
            name="search_experience_knowledge_base",
            description=search_experience_knowledge_base_description,
            func=self.invoke,   
            coroutine=self.ainvoke,
            args_schema=SearchExperienceKBSchema
        )
    
    def invoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.experience_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = retriever.invoke(input)
            return SearchExperienceKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching experience knowledge base: {e}")
            return f"Error searching experience knowledge base: {e}"
    async def ainvoke(
        self, 
        query: str,
    ) -> str:
        try:
            input = RetrieverModel(
                query=query,
                collection_name=_settings.qdrant.experience_collection,
                kb_ids=self.kb_ids,
                limit=_settings.qdrant.limit
            )
            response = await retriever.ainvoke(input)
            return SearchExperienceKnowledgeBaseTool.format_response(response)
        except Exception as e:
            logger.error(f"Error searching experience knowledge base: {e}")
            return f"Error searching experience knowledge base: {e}"
    
    @staticmethod
    def format_response(response: RetrieverModelResponse) -> str:
        formatted_results = []
        for result in response.results:
            formatted_results.append(format_experience_response(result))
        return "\n".join(formatted_results)

class FillingExperienceTicketTool(BaseTool):
    """
    Tool for filling experience ticket.
    """
    def __init__(self):
        super().__init__(name="filling_experience_ticket", description=filling_experience_ticket_description)
        self.tool = StructuredTool(
            name="filling_experience_ticket",
            description=filling_experience_ticket_description,
            func=self.invoke,
            # coroutine=self.ainvoke,
            args_schema=FillingExperienceTicketSchema
        )
        
    def invoke(
        self, 
        error_title: str = "",
        error_code: str = "", 
        device: str = "", 
        serial_number: str = "", 
        error_component: str = "",
        priority: str = "",
        severity: str = "",
        occurred_at: str = "",
        symptoms: str = "", 
        root_cause: str = "", 
        steps_to_reproduce: str = "", 
        workaround: str = "", 
        resolution_steps: str = "", 
        time_spent_mins: int = "", 
        material_cost_used: float = 0
    ) -> str:
        
        params_mapping = {
            "errorTitle": error_title,
            "errorCode": error_code,
            "device": device,
            "serialNumber": serial_number,
            "errorComponent": error_component,
            "priority": priority,
            "severity": severity,
            "occurredAt": occurred_at,
            "symptoms": symptoms,
            "rootCause": root_cause,
            "stepsToReproduce": steps_to_reproduce,
            "workaround": workaround,
            "resolutionSteps": resolution_steps,
            "timeSpentMins": time_spent_mins,
            "materialCostUsed": material_cost_used
        }
        return f"{_settings.web.fe_url}/corrective-actions/new?{urllib.parse.urlencode(params_mapping)}"

    async def ainvoke(self) -> str:
        pass

class TavilyWebSearchTool(BaseTool):
    """
    Tool for searching the web.
    """
    def __init__(self):
        super().__init__(name="tavily_search", description=tavily_search_description)
        self.tool = StructuredTool(
            name="tavily_search",
            description=tavily_search_description,
            func=self.invoke,
            coroutine=self.ainvoke,
            args_schema=TavilySearchSchema
        )
    
    def invoke(
        self,
        query: str,
    ) -> str:
        try:
            raw = tavily_search.invoke(query)
            return format_web_search_response(query, raw)
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return f"Error searching web: {e}"
    async def ainvoke(
        self,
        query: str,
    ) -> str:
        try:
            raw = await tavily_search.ainvoke(query)
            return format_web_search_response(query, raw)
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return f"Error searching web: {e}"
        