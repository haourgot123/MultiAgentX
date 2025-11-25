from pydantic import BaseModel, Field
from typing import Literal

class SearchDefaultKBSchema(BaseModel):
    query: str = Field(..., description="The natural-language question or topic to search for.")
    domain: Literal["fanuc", "mitsubishi"] = Field(default="fanuc", description="The manufacturer or product domain context. Defaults to 'fanuc'.")
    
class SearchCompanyKBSchema(BaseModel):
    query: str = Field(..., description="The question or keyword describing what to search within the company-level knowledge base.")
    
class SearchProjectKBSchema(BaseModel):
    query: str = Field(..., description="The question or keyword describing what to search within the project-level knowledge base.")
    
class SearchExperienceKBSchema(BaseModel):
    query: str = Field(..., description="The question or keyword describing what to search within the experience-level knowledge base.")
    
class FillingExperienceTicketSchema(BaseModel):
    error_title: str = Field(..., description="The title of the error or issue.")
    error_code: str = Field(..., description="The code of the error or issue.")
    device: str = Field(..., description="The device or machine model.")
    serial_number: str = Field(..., description="The serial number of the device or machine.")
    error_component: str = Field(..., description="The component or part of the device or machine that is causing the error or issue.")
    priority: str = Field(..., description="The priority of the error or issue.")
    severity: str = Field(..., description="The severity of the error or issue.")
    occurred_at: str = Field(..., description="The date and time the error or issue occurred.")
    symptoms: str = Field(..., description="The symptoms of the error or issue.")
    root_cause: str = Field(..., description="The root cause of the error or issue.")
    steps_to_reproduce: str = Field(..., description="The steps to reproduce the error or issue.")
    workaround: str = Field(..., description="The workaround for the error or issue.")
    resolution_steps: str = Field(..., description="The steps to resolve the error or issue.")
    time_spent_mins: int = Field(..., description="The time spent resolving the error or issue.")
    material_cost_used: float = Field(..., description="The cost of the materials used to resolve the error or issue.")
    
class TavilySearchSchema(BaseModel):
    query: str = Field(..., description="The natural-language question or topic to search for.")

class AuthenCheckSchema(BaseModel):
    serial_number: str = Field(..., description="The serial number of the product to check authentication of.")