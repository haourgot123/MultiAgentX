from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from ..services.agent_service import chat_response_streamer
from ..schemas.agent_schema import (
    ChatConversationSchema,
    AgentType
)

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/", status_code=status.HTTP_200_OK, description="Get agents")
async def get_agents():
    return [agent.value for agent in AgentType]

@router.post("/{agent_type}/chat", status_code=status.HTTP_200_OK, description="Chat with an agent")
async def chat_with_agent(
    agent_type: AgentType,
    request: ChatConversationSchema
):
    async def event_stream():
        async for chunk in chat_response_streamer(
            agent_type, 
            request.user_id, 
            request.session_id, 
            request.user_message, 
            request.knowledge_bases, 
            request.documents, 
            request.deep_research, 
            request.stream
        ):
            yield f"event: {chunk.event}\ndata: {chunk.model_dump_json()}\n\n".encode("utf-8")
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")