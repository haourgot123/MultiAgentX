from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import Runnable

from backend.agents.video_generation_agent.state import VideoGenerationAgentState


class RemotionInputNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "remotion_input",
                "message": "Preparing Remotion input...",
            },
        )

        return {
            "remotion_input": {
                "jobId": state.job_id,
                "prompt": state.prompt,
                "style": state.style,
                "durationSeconds": state.duration_seconds,
                "fps": state.fps,
                "width": state.width,
                "height": state.height,
                "aspectRatio": state.aspect_ratio,
                "scenes": [scene.model_dump() for scene in state.storyboard],
                "sources": [source.model_dump() for source in state.sources],
            }
        }
