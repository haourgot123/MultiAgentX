from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.agents.video_generation_agent.nodes import (
    AssetNode,
    OptionalResearchNode,
    RemotionInputNode,
    RenderNode,
    StoryboardNode,
    StreamResultNode,
    ValidateSettingsNode,
)
from backend.agents.video_generation_agent.state import Node, VideoGenerationAgentState


class VideoGenerationAgentGraph:
    def __init__(self):
        self.graph = StateGraph(VideoGenerationAgentState)
        self.compiled_graph = self._compile_graph()
        self.runnable_config = self._config_graph()

    def _config_graph(
        self,
        metadata: Dict = None,
        tags: List[str] = None,
        max_concurrency: Optional[int] = 4,
        recursion_limit: Optional[int] = 30,
    ) -> RunnableConfig:
        return RunnableConfig(
            metadata=metadata,
            tags=tags or ["video_generation_graph"],
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _add_graph_nodes(self):
        self.graph.add_node(
            Node.video_generation_agent_validate_settings_node.name,
            ValidateSettingsNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_optional_research_node.name,
            OptionalResearchNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_storyboard_node.name,
            StoryboardNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_asset_node.name,
            AssetNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_remotion_input_node.name,
            RemotionInputNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_render_node.name,
            RenderNode().ainvoke,
        )
        self.graph.add_node(
            Node.video_generation_agent_stream_result_node.name,
            StreamResultNode().ainvoke,
        )

    def _add_graph_edges(self):
        self.graph.add_edge(START, Node.video_generation_agent_validate_settings_node.name)
        self.graph.add_edge(
            Node.video_generation_agent_validate_settings_node.name,
            Node.video_generation_agent_optional_research_node.name,
        )
        self.graph.add_edge(
            Node.video_generation_agent_optional_research_node.name,
            Node.video_generation_agent_storyboard_node.name,
        )
        self.graph.add_edge(
            Node.video_generation_agent_storyboard_node.name,
            Node.video_generation_agent_asset_node.name,
        )
        self.graph.add_edge(
            Node.video_generation_agent_asset_node.name,
            Node.video_generation_agent_remotion_input_node.name,
        )
        self.graph.add_edge(
            Node.video_generation_agent_remotion_input_node.name,
            Node.video_generation_agent_render_node.name,
        )
        self.graph.add_edge(
            Node.video_generation_agent_render_node.name,
            Node.video_generation_agent_stream_result_node.name,
        )
        self.graph.add_edge(Node.video_generation_agent_stream_result_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    async def stream(self, inputs: dict) -> AsyncGenerator[Dict[str, Any], None]:
        final_state: dict[str, Any] | None = None
        async for event in self.compiled_graph.astream_events(
            input=inputs,
            config=self.runnable_config,
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_custom_event":
                event_name = event.get("name", "")
                event_data = event.get("data", {})
                if event_name in {"status", "storyboard"}:
                    yield {"type": event_name, **event_data}
            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, dict) and "job_id" in output and "remotion_input" in output:
                    final_state = output

        if final_state:
            yield {"type": "result", "state": final_state}
