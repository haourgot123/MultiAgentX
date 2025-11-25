from pydantic import BaseModel, Field
from typing import List, Literal
from enum import Enum

class AgentType(str, Enum):
    ANSWER_GENERATION = "agent_answer_generation"
    AGENT_PRESSROOM = "agent_pressroom"
    AGENT_AUTHENTICATION = "agent_authentication"
    
    
class KnowledgeBaseSchema(BaseModel):
    name: Literal["default", "company", "project"] = Field(..., description="The name of the knowledge base")
    kb_ids: List[str] = Field(..., description="The IDs of the knowledge bases")

class ChatConversationSchema(BaseModel):
    user_id: str = Field(..., description="The user ID of the user who is having the conversation")
    session_id: str = Field(..., description="The session ID of the conversation")
    user_message: str = Field(..., description="The message from the user")
    knowledge_bases: List[KnowledgeBaseSchema] = Field(..., description="The knowledge bases to use for the conversation")
    documents: List[str] = Field(default = [], description="The documents to use for the conversation")
    deep_research: bool = Field(default = False, description="Whether to use deep research for the conversation")
    stream: bool = Field(default = True, description="Whether to stream the conversation")

class ChatResponseEvent(BaseModel):
    event: str = Field(..., description="The event of the response")
    content: str = Field(..., description="The content of the response")
