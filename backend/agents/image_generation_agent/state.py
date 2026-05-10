from enum import Enum, auto
from typing import Any, List
from pydantic import BaseModel


class ImageGenerationAgentState(BaseModel):
    user_question: str
    user_id: int = 0
    memories: List[Any] = []
    enhanced_prompt: str = ""
    image_urls: List[str] = []
    revised_prompt: str = ""
    error_message: str = ""
    output: str = ""
    blob_path: str = ""
    blob_name: str = ""
    blob_content_type: str = ""
    blob_size: int = 0


class Node(Enum):
    image_generation_agent_prompt_enhance_node = auto()
    image_generation_agent_generate_node = auto()
    image_generation_agent_stream_node = auto()


class Tag(Enum):
    streaming_node = auto()
    generation_node = auto()
