from ..schemas.agent_schema import AgentType
from app.agent.core.agents.factory import AgentFactory
from typing import AsyncGenerator, Optional, List, Dict, Any
from ..schemas.agent_schema import ChatResponseEvent

async def chat_response_streamer(
    agent_type: AgentType,
    user_id: str,
    session_id: str,
    user_message: str,
    knowledge_bases: List[Dict[str, Any]],
    documents: Optional[List[str]] = None,
    deep_research: bool = False,
    stream: bool = True,
) -> AsyncGenerator[ChatResponseEvent, None]:
    
    # agent = AgentFactory().create_agent(agent_type)
    for i in range(100):
        yield ChatResponseEvent(event="RunStart", content=f"Run started {i}")
        yield ChatResponseEvent(event="RunContent", content=f"Run content {i}")
        yield ChatResponseEvent(event="RunEnd", content=f"Run ended {i}")