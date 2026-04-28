from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import Runnable

from backend.agents.video_generation_agent.state import VideoGenerationAgentState


class StreamResultNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "finalizing",
                "message": "Finalizing video result...",
            },
        )
        return {}
