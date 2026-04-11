from typing import Dict, List, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, Node, Tag
from backend.agents.rag_agent.nodes.query_transform_node import QueryTransformNode
from backend.agents.rag_agent.nodes.retrieve_node import RetrieveNode
from backend.agents.rag_agent.nodes.rerank_node import RerankNode
from backend.agents.rag_agent.nodes.synthesize_node import SynthesizeNode
from backend.agents.rag_agent.nodes.stream_node import StreamNode


service_logger = logger.bind(service="rag-agent-graph")


class RAGAgentGraph:
    def __init__(self):
        self.graph = StateGraph(RAGAgentState)
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
            tags = ["rag_graph"]
        return RunnableConfig(
            metadata=metadata,
            tags=tags,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _add_graph_nodes(self):
        self.graph.add_node(Node.rag_agent_query_transform_node.name, QueryTransformNode().ainvoke)
        self.graph.add_node(Node.rag_agent_retrieve_node.name, RetrieveNode().ainvoke)
        self.graph.add_node(Node.rag_agent_rerank_node.name, RerankNode().ainvoke)
        self.graph.add_node(Node.rag_agent_synthesize_node.name, SynthesizeNode().ainvoke)
        self.graph.add_node(Node.rag_agent_stream_node.name, StreamNode().ainvoke)

    def _add_graph_edges(self):
        self.graph.add_edge(START, Node.rag_agent_query_transform_node.name)
        self.graph.add_edge(Node.rag_agent_query_transform_node.name, Node.rag_agent_retrieve_node.name)
        self.graph.add_edge(Node.rag_agent_retrieve_node.name, Node.rag_agent_rerank_node.name)
        self.graph.add_edge(Node.rag_agent_rerank_node.name, Node.rag_agent_synthesize_node.name)
        self.graph.add_edge(Node.rag_agent_synthesize_node.name, Node.rag_agent_stream_node.name)
        self.graph.add_edge(Node.rag_agent_stream_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    def visualize_graph(self, visualization_type: str = "ascii") -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()