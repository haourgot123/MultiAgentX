from typing import Dict, List, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from backend.agents.image_generation_agent.state import ImageGenerationAgentState, Node, Tag
from backend.agents.image_generation_agent.nodes.prompt_enhance_node import PromptEnhanceNode
from backend.agents.image_generation_agent.nodes.generate_node import GenerateNode
from backend.agents.image_generation_agent.nodes.stream_node import StreamNode


service_logger = logger.bind(service="image-generation-graph")


class ImageGenerationAgentGraph:
    def __init__(self):
        self.graph = StateGraph(ImageGenerationAgentState)
        self.compiled_graph = self._compile_graph()
        self.runnable_config = self._config_graph()

    def _config_graph(
        self,
        metadata: Dict = None,
        tags: List[str] = None,
        max_concurrency: Optional[int] = 20,
        recursion_limit: Optional[int] = 50,
    ) -> RunnableConfig:
        if tags is None:
            tags = ["image_generation_graph"]
        return RunnableConfig(
            metadata=metadata,
            tags=tags,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _add_graph_nodes(self):
        self.graph.add_node(Node.image_generation_agent_prompt_enhance_node.name, PromptEnhanceNode().ainvoke)
        self.graph.add_node(Node.image_generation_agent_generate_node.name, GenerateNode().ainvoke)
        self.graph.add_node(Node.image_generation_agent_stream_node.name, StreamNode().ainvoke)

    def _add_graph_edges(self):
        self.graph.add_edge(START, Node.image_generation_agent_prompt_enhance_node.name)
        self.graph.add_edge(Node.image_generation_agent_prompt_enhance_node.name, Node.image_generation_agent_generate_node.name)
        self.graph.add_edge(Node.image_generation_agent_generate_node.name, Node.image_generation_agent_stream_node.name)
        self.graph.add_edge(Node.image_generation_agent_stream_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    def visualize_graph(self, visualization_type: str = "ascii") -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()