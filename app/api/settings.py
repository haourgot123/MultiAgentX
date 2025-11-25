from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from app.config.settings import _settings
class ApiSettings(BaseSettings):
    title: str
    version: str
    docs_enabled: bool
    cors_origin_list: Optional[List[str]] = Field(default=None, validate_default=True)

    @field_validator("cors_origin_list", mode="before")
    def set_cors_origin_list(
        cls, cors_origin_list: Optional[List[str]], info: FieldValidationInfo) -> List[str]:
        provided: List[str] = cors_origin_list or []
        merged: List[str] = []
        for origin in [*provided, *_settings.api.cors_origins]:
            if origin and origin not in merged:
                merged.append(origin)
        return merged

api_settings = ApiSettings(
    title=_settings.api.title,
    version=_settings.api.version,
    docs_enabled=_settings.api.docs_enabled,
    cors_origin_list=_settings.api.cors_origins,
)