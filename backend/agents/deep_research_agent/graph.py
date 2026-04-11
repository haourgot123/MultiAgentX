from typing import Dict, List, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState, Node
from backend.agents.deep_research_agent.nodes.plan_node import PlanNode
from backend.agents.deep_research_agent.nodes.query_generation_node import QueryGenerationNode
from backend.agents.deep_research_agent.nodes.search_node import SearchNode
from backend.agents.deep_research_agent.nodes.analyze_node import AnalyzeNode
from backend.agents.deep_research_agent.nodes.should_continue_node import ShouldContinueNode
from backend.agents.deep_research_agent.nodes.synthesize_node import SynthesizeNode


service_logger = logger.bind(service="deep-research-graph")


class DeepResearchAgentGraph:
    def __init__(self, max_iterations: int = 3, plan_only: bool = False):
        self.graph = StateGraph(DeepResearchAgentState)
        self.max_iterations = max_iterations
        self.plan_only = plan_only
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
            tags = ["deep_research_graph"]
        return RunnableConfig(
            metadata=metadata,
            tags=tags,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _add_graph_nodes(self):
        self.graph.add_node(Node.deep_research_agent_plan_node.name, PlanNode().ainvoke)
        self.graph.add_node(Node.deep_research_agent_query_generation_node.name, QueryGenerationNode().ainvoke)
        self.graph.add_node(Node.deep_research_agent_search_node.name, SearchNode().ainvoke)
        self.graph.add_node(Node.deep_research_agent_analyze_node.name, AnalyzeNode().ainvoke)
        self.graph.add_node(Node.deep_research_agent_should_continue_node.name, ShouldContinueNode().ainvoke)
        self.graph.add_node(Node.deep_research_agent_synthesize_node.name, SynthesizeNode().ainvoke)

    def _should_continue(self, state: DeepResearchAgentState) -> str:
        if state.need_more_research and state.current_iteration < state.max_iterations:
            return "continue"
        return "synthesize"

    def _add_graph_edges(self):
        self.graph.add_edge(START, Node.deep_research_agent_plan_node.name)
        
        # If plan_only mode, stop after plan node
        if self.plan_only:
            self.graph.add_edge(Node.deep_research_agent_plan_node.name, END)
        else:
            self.graph.add_edge(Node.deep_research_agent_plan_node.name, Node.deep_research_agent_query_generation_node.name)
            self.graph.add_edge(Node.deep_research_agent_query_generation_node.name, Node.deep_research_agent_search_node.name)
            self.graph.add_edge(Node.deep_research_agent_search_node.name, Node.deep_research_agent_analyze_node.name)
            self.graph.add_edge(Node.deep_research_agent_analyze_node.name, Node.deep_research_agent_should_continue_node.name)
            
            self.graph.add_conditional_edges(
                Node.deep_research_agent_should_continue_node.name,
                self._should_continue,
                {
                    "continue": Node.deep_research_agent_query_generation_node.name,
                    "synthesize": Node.deep_research_agent_synthesize_node.name,
                },
            )
            
            # SynthesizeNode now streams LLM tokens natively via tags — connect directly to END
            self.graph.add_edge(Node.deep_research_agent_synthesize_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    def visualize_graph(self, visualization_type: str = "ascii") -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()