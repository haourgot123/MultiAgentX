import asyncio
from typing import AsyncGenerator, List, Any, Optional, Dict
from langgraph.graph import StateGraph, END, START
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from backend.agents.general_agent.tools.websearch import SearchResults
from backend.agents.websearch_agent.nodes.transform_query_node import TransformQueryNode
from backend.agents.websearch_agent.nodes.search_node import SearchNode
from langgraph.graph.state import CompiledStateGraph
from backend.agents.websearch_agent.nodes.stream_node import StreamNode
from backend.agents.general_agent.state import Tag, Node
from backend.agents.websearch_agent.state import WebsearchAgentState

class WebSearchAgentGraph:
    def __init__(
        self,
    ):
        self.graph = StateGraph(WebsearchAgentState)
        self.compiled_graph = self._compile_graph()
        self.runnable_config = self._config_graph()

    def _config_graph(
        self,
        metadata: Dict = None,
        tags: List[str] = ["websearch_graph"],
        max_concurrency: Optional[int] = 20,
        recursion_limit: int = 50,
    ) -> RunnableConfig:
        return RunnableConfig(
            metadata=metadata,
            tags=tags,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    def _add_graph_nodes(self):
        # Add memory constructor node
        # self.graph.add_node(Node.locator_node.name, HeadquarterLocatorNode().ainvoke)
        self.graph.add_node(Node.websearch_agent_transform_query_node.name, TransformQueryNode().ainvoke)
        self.graph.add_node(Node.websearch_agent_search_node.name, SearchNode().ainvoke)
        self.graph.add_node(Node.websearch_agent_stream_node.name, StreamNode().ainvoke)

    def _add_graph_edges(self):

        self.graph.add_edge(START, Node.websearch_agent_transform_query_node.name)
        self.graph.add_edge(Node.websearch_agent_transform_query_node.name, Node.websearch_agent_search_node.name)
        self.graph.add_edge(Node.websearch_agent_search_node.name, Node.websearch_agent_stream_node.name)
        self.graph.add_edge(Node.websearch_agent_stream_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        # Add graph nodes
        self._add_graph_nodes()

        # Add graph edges
        self._add_graph_edges()

        return self.graph.compile()

    def visualize_graph(
        self,
        visualization_type: str = "ascii",
        save_graph_path: str = "graph_visualization.png",
    ) -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()

    async def stream(self, inputs: dict) -> AsyncGenerator[str, None]:
        config = self._config_graph()
        graph = self.compiled_graph
        try:
            async for event in graph.astream_events(
                input=inputs,
                config=config,
                version="v2",
            ):
                kind = event["event"]
                tags = event.get("tags", [])

                # Handle end of chain
                if kind == "on_chain_end" and any(
                    tag in [tag_name.name for tag_name in Tag] for tag in tags
                ):
                    if any(
                        tag
                        in [
                            tag_name.name
                            for tag_name in [Tag.explanation_node, Tag.retrieval_progress_node]
                        ]
                        for tag in tags
                    ):
                        list_data = event["data"]["output"].split(" ")
                        for token in list_data: 
                            yield token + " "
                            await asyncio.sleep(0.01)
                    elif any(
                        tag in [tag_name.name for tag_name in [Tag.direct_response_node]]
                        for tag in tags
                    ):
                        list_data = event["data"]["output"].split(" ")
                        for token in list_data:
                            yield token + " "
                            await asyncio.sleep(0.005)
                    else:
                        yield event["data"]["output"]

                # Handle streaming chunk
                if kind == "on_chat_model_stream" and Tag.streaming_node.name in tags:
                    yield event["data"]["chunk"].content
        finally:
            # Explicit cleanup
            del graph
