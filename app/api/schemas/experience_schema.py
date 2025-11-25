from typing import Optional, Literal
from pydantic import BaseModel, Field


class ExperienceRequest(BaseModel):
    knowledge_base_id: str = Field(..., description="ID knowledge base")
    error_title: str = Field(..., description="Error Title")
    error_code: str = Field(..., description="Error Code")
    device: str = Field(..., description="Device")
    serial_number: str = Field(..., description="Serial Number")
    priority: str = Field(..., description="Priority")
    severity: str = Field(..., description="Severity")
    occurred_at: str = Field(..., description="Occurred At (ISO or text)")
    error_component: str = Field(..., description="Error Component")
    symptoms: str = Field(..., description="Symptoms")
    firmware_version: Optional[str] = Field(None, description="Firmware Version")
    steps_to_reproduce: str = Field(..., description="Steps to Reproduce")
    root_cause: Optional[str] = Field(None, description="Root Cause")
    workaround: Optional[str] = Field(None, description="Workaround")
    resolution_steps: str = Field(..., description="Resolution Steps")
    time_spent_mins: Optional[int] = Field(None, description="Time Spent (minutes)")
    material_cost_used: Optional[float] = Field(None, description="Material Cost Used")

class MessageResponse(BaseModel):
    status: Literal["success", "failed"] = Field(..., description="Status of the response")
    message: str = Field(..., description="Message of the response")
    