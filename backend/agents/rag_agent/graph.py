from typing import Dict, List, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, Node, Tag
from backend.agents.rag_agent.nodes.query_transform_node import QueryTransformNode
from backend.agents.rag_agent.nodes.retrieve_node import RetrieveNode
from backend.agents.rag_agent.nodes.combine_context_node import CombineContextNode
from backend.agents.rag_agent.nodes.evaluation_node import EvaluationNode
from backend.agents.rag_agent.nodes.synthesize_node import SynthesizeNode




class RAGAgentGraph:
    """
    RAG Agent with evaluation-retry loop.

    Graph topology:
        START → QueryTransform → Retrieve → CombineContext → Evaluation
                     ↑                                           ↓
                     └──── (retry if NOT relevant & retries < 3) ┘
                                                                 ↓
                                                          SynthesizeNode → END
    """

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
        self.graph.add_node(
            Node.rag_agent_query_transform_node.name,
            QueryTransformNode().ainvoke,
        )
        self.graph.add_node(
            Node.rag_agent_retrieve_node.name,
            RetrieveNode().ainvoke,
        )
        self.graph.add_node(
            Node.rag_agent_combine_context_node.name,
            CombineContextNode().ainvoke,
        )
        self.graph.add_node(
            Node.rag_agent_evaluation_node.name,
            EvaluationNode().ainvoke,
        )
        self.graph.add_node(
            Node.rag_agent_synthesize_node.name,
            SynthesizeNode().ainvoke,
        )

    @staticmethod
    def _route_after_evaluation(state: RAGAgentState) -> str:
        """
        Conditional edge after EvaluationNode:
        - If relevant → SynthesizeNode
        - If NOT relevant AND retries < max → QueryTransformNode (retry)
        - If NOT relevant AND retries >= max → SynthesizeNode (best-effort / empty context)
        """
        if state.is_relevant:
            return Node.rag_agent_synthesize_node.name

        if state.retry_count < state.max_retries:
            logger.info(
                f"[RAGAgentGraph] Evaluation: not relevant, retry {state.retry_count}/{state.max_retries} → re-transform query"
            )
            return Node.rag_agent_query_transform_node.name

        logger.info(
            f"[RAGAgentGraph] Evaluation: not relevant, max retries reached ({state.max_retries}) → synthesize anyway"
        )
        return Node.rag_agent_synthesize_node.name

    def _add_graph_edges(self):
        # Linear flow: START → QueryTransform → Retrieve → CombineContext → Evaluation
        self.graph.add_edge(START, Node.rag_agent_query_transform_node.name)
        self.graph.add_edge(
            Node.rag_agent_query_transform_node.name,
            Node.rag_agent_retrieve_node.name,
        )
        self.graph.add_edge(
            Node.rag_agent_retrieve_node.name,
            Node.rag_agent_combine_context_node.name,
        )
        self.graph.add_edge(
            Node.rag_agent_combine_context_node.name,
            Node.rag_agent_evaluation_node.name,
        )

        # Conditional edge: Evaluation → Synthesize OR → QueryTransform (retry)
        self.graph.add_conditional_edges(
            Node.rag_agent_evaluation_node.name,
            self._route_after_evaluation,
            {
                Node.rag_agent_synthesize_node.name: Node.rag_agent_synthesize_node.name,
                Node.rag_agent_query_transform_node.name: Node.rag_agent_query_transform_node.name,
            },
        )

        # Synthesize → END
        self.graph.add_edge(Node.rag_agent_synthesize_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    def visualize_graph(self, visualization_type: str = "ascii") -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()