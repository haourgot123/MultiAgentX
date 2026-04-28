from enum import Enum, auto
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from backend.agents.general_agent.tools.websearch import SearchResults


class VideoScene(BaseModel):
    index: int
    title: str
    narration: str
    visual_prompt: str
    on_screen_text: str
    duration_seconds: int
    image_url: Optional[str] = None


class VideoGenerationAgentState(BaseModel):
    job_id: int
    user_id: int
    prompt: str
    duration_seconds: int
    fps: int
    aspect_ratio: str
    style: str
    web_search_enabled: bool = True
    width: int = 1280
    height: int = 720
    sources: List[SearchResults] = Field(default_factory=list)
    storyboard: List[VideoScene] = Field(default_factory=list)
    remotion_input: dict[str, Any] = Field(default_factory=dict)
    workdir: Optional[Path] = None
    video_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    error_message: str = ""


class Node(Enum):
    video_generation_agent_validate_settings_node = auto()
    video_generation_agent_optional_research_node = auto()
    video_generation_agent_storyboard_node = auto()
    video_generation_agent_asset_node = auto()
    video_generation_agent_remotion_input_node = auto()
    video_generation_agent_render_node = auto()
    video_generation_agent_stream_result_node = auto()
