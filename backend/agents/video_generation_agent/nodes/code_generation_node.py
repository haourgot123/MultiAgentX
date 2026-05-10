from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import Runnable

from backend.agents.video_generation_agent.codegen import generate_remotion_entry
from backend.agents.video_generation_agent.state import VideoGenerationAgentState


class CodeGenerationNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "code_generation",
                "message": "Generating dynamic Remotion composition code...",
            },
        )

        composition_code = await generate_remotion_entry(
            remotion_input=state.remotion_input,
            creative_direction=state.creative_direction,
            composition_id=state.composition_id,
            skill_bundle=state.skill_bundle,
        )

        return {"composition_code": composition_code}
