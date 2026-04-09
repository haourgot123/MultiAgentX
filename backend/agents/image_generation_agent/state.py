from enum import Enum, auto
from typing import Any, List
from pydantic import BaseModel


class ImageGenerationAgentState(BaseModel):
    user_question: str
    memories: List[Any] = []
    enhanced_prompt: str = ""
    image_urls: List[str] = []
    revised_prompt: str = ""
    error_message: str = ""


class Node(Enum):
    image_generation_agent_prompt_enhance_node = auto()
    image_generation_agent_generate_node = auto()
    image_generation_agent_stream_node = auto()


class Tag(Enum):
    streaming_node = auto()
    generation_node = auto()