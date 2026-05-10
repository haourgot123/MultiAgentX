from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import Runnable

from backend.agents.video_generation_agent.skills import load_remotion_skill_bundle
from backend.agents.video_generation_agent.state import VideoGenerationAgentState


class LoadSkillNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "skills",
                "message": "Loading Remotion skill guidance...",
            },
        )

        skill_bundle = load_remotion_skill_bundle()
        await adispatch_custom_event(
            "status",
            {
                "step": "skills",
                "message": "Loaded Remotion best-practices skill for storyboard and code generation.",
            },
        )
        return {"skill_bundle": skill_bundle}
