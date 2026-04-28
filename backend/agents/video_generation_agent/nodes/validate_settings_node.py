from langchain_core.callbacks import dispatch_custom_event
from langchain_core.runnables import Runnable

from backend.agents.video_generation_agent.state import VideoGenerationAgentState
from backend.config.settings import _settings


ASPECT_RATIO_DIMENSIONS = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (1080, 1080),
}


class ValidateSettingsNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "validate",
                "message": "Validating video settings...",
            },
        )

        max_duration = _settings.video_generation.max_duration_seconds
        duration = min(max(state.duration_seconds, 5), max_duration)
        fps = state.fps if state.fps in {24, 30} else _settings.video_generation.default_fps
        if duration * fps > max_duration * 30:
            duration = max_duration
            fps = min(fps, 30)

        width, height = ASPECT_RATIO_DIMENSIONS.get(state.aspect_ratio, (1280, 720))

        return {
            "duration_seconds": duration,
            "fps": fps,
            "width": width,
            "height": height,
        }
