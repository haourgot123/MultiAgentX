import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from backend.agents.general_agent.state import GeneralAgentState, Node, Tag
from backend.agents.general_agent.nodes.route_node import RouteNode
from backend.agents.general_agent.nodes.answer_node import AnswerNode
from backend.agents.general_agent.nodes.memory_node import MemoryNode
from backend.agents.general_agent.nodes.stream_node import StreamNode

from backend.agents.websearch_agent.graph import (
    WebSearchAgentGraph,
    WebsearchAgentState,
)
from backend.agents.rag_agent.graph import RAGAgentGraph
from backend.agents.rag_agent.state import RAGAgentState
from backend.agents.image_generation_agent.graph import ImageGenerationAgentGraph
from backend.agents.image_generation_agent.state import ImageGenerationAgentState
from backend.agents.deep_research_agent.graph import DeepResearchAgentGraph
from backend.agents.deep_research_agent.state import DeepResearchAgentState

from langchain_core.callbacks import dispatch_custom_event


class GeneralAgentGraph:
    def __init__(
        self,
    ):
        self.graph = StateGraph(GeneralAgentState)
        self.compiled_graph = self._compile_graph()
        self.runnable_config = self._config_graph()

    def _config_graph(
        self,
        metadata: Dict = None,
        tags: List[str] = ["general_graph"],
        max_concurrency: Optional[int] = 20,
        recursion_limit: Optional[int] = 50,
    ) -> RunnableConfig:
        return RunnableConfig(
            metadata=metadata,
            tags=tags,
            max_concurrency=max_concurrency,
            recursion_limit=recursion_limit,
        )

    async def call_websearch_agent(
        self, state: GeneralAgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        """Wrapper to call the websearch subgraph"""
        logger.info("Delegating to websearch_agent...")
        dispatch_custom_event(
            "status",
            {
                "step": "websearch_delegate",
                "message": "🌐 Switching to the web search agent...",
            },
        )
        websearch_state = WebsearchAgentState(
            user_question=state.user_question, search_query="", memories=state.memories
        )
        web_graph = WebSearchAgentGraph().compiled_graph
        result_state = await web_graph.ainvoke(websearch_state, config=config)
        return {
            "websearch_results": result_state.get("search_results", []),
            "output": result_state.get("output", ""),
        }

    async def call_rag_agent(
        self, state: GeneralAgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        """Wrapper to call the RAG subgraph"""
        logger.info("Delegating to rag_agent...")
        dispatch_custom_event(
            "status",
            {
                "step": "rag_delegate",
                "message": "📚 Switching to document search agent...",
            },
        )
        rag_state = RAGAgentState(
            user_question=state.user_question,
            memories=state.memories,
            user_id=state.user_id,
            file_ids=state.file_ids,
        )
        rag_graph = RAGAgentGraph().compiled_graph
        result_state = await rag_graph.ainvoke(rag_state, config=config)
        return {
            "output": result_state.get("final_answer", result_state.get("output", "")),
        }

    async def call_image_generation_agent(
        self, state: GeneralAgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        """Wrapper to call the image generation subgraph"""
        logger.info("Delegating to image_generation_agent...")
        dispatch_custom_event(
            "status",
            {
                "step": "image_generation_delegate",
                "message": "🎨 Switching to image generation agent...",
            },
        )
        image_state = ImageGenerationAgentState(
            user_question=state.user_question,
            memories=state.memories,
        )
        image_graph = ImageGenerationAgentGraph().compiled_graph
        result_state = await image_graph.ainvoke(image_state, config=config)
        return {
            "output": result_state.get("output", ""),
        }

    async def call_deep_research_agent(
        self, state: GeneralAgentState, config: RunnableConfig
    ) -> Dict[str, Any]:
        """Wrapper to call the deep research subgraph"""
        logger.info("Delegating to deep_research_agent...")
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_delegate",
                "message": "🔬 Switching to deep research agent...",
            },
        )
        research_state = DeepResearchAgentState(
            user_question=state.user_question,
            memories=state.memories,
            max_iterations=3,
        )
        research_graph = DeepResearchAgentGraph().compiled_graph
        result_state = await research_graph.ainvoke(research_state, config=config)
        return {
            "output": result_state.get("final_report", result_state.get("output", "")),
        }

    def _add_graph_nodes(self):
        self.graph.add_node(Node.general_agent_memory_node.name, MemoryNode().ainvoke)
        self.graph.add_node(Node.general_agent_route_node.name, RouteNode().ainvoke)
        self.graph.add_node(Node.general_agent_answer_node.name, AnswerNode().ainvoke)
        self.graph.add_node(Node.general_agent_stream_node.name, StreamNode().ainvoke)

        self.graph.add_node("websearch_agent", self.call_websearch_agent)
        self.graph.add_node("rag_agent", self.call_rag_agent)
        self.graph.add_node("image_generation_agent", self.call_image_generation_agent)
        self.graph.add_node("deep_research_agent", self.call_deep_research_agent)

    def _route_after_decision(self, state: GeneralAgentState) -> str:
        """Determines the next edge based on the assigned route."""
        route = getattr(state, "route", "direct_response")

        route_mapping = {
            "websearch_agent": "websearch_agent",
            "rag_agent": "rag_agent",
            "image_generation_agent": "image_generation_agent",
            "deep_research_agent": "deep_research_agent",
        }
        
        return route_mapping.get(route, Node.general_agent_answer_node.name)

    def _add_graph_edges(self):
        self.graph.add_edge(START, Node.general_agent_memory_node.name)
        self.graph.add_edge(
            Node.general_agent_memory_node.name, Node.general_agent_route_node.name
        )

        self.graph.add_conditional_edges(
            Node.general_agent_route_node.name,
            self._route_after_decision,
            {
                "websearch_agent": "websearch_agent",
                "rag_agent": "rag_agent",
                "image_generation_agent": "image_generation_agent",
                "deep_research_agent": "deep_research_agent",
                Node.general_agent_answer_node.name: Node.general_agent_answer_node.name,
            },
        )

        self.graph.add_edge("websearch_agent", Node.general_agent_stream_node.name)
        self.graph.add_edge("rag_agent", Node.general_agent_stream_node.name)
        self.graph.add_edge("image_generation_agent", Node.general_agent_stream_node.name)
        self.graph.add_edge("deep_research_agent", Node.general_agent_stream_node.name)
        self.graph.add_edge(
            Node.general_agent_answer_node.name, Node.general_agent_stream_node.name
        )

        self.graph.add_edge(Node.general_agent_stream_node.name, END)

    def _compile_graph(self) -> CompiledStateGraph:
        self._add_graph_nodes()
        self._add_graph_edges()
        return self.graph.compile()

    def visualize_graph(
        self,
        visualization_type: str = "ascii",
        save_graph_path: str = "graph_visualization.png",
    ) -> Optional[str]:
        if visualization_type == "ascii":
            self.compiled_graph.get_graph().print_ascii()

    async def stream(self, inputs: dict) -> AsyncGenerator[Dict[str, Any], None]:
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

                if kind == "on_chain_end" and any(
                    tag in [tag_name.name for tag_name in Tag] for tag in tags
                ):
                    if any(
                        tag
                        in [
                            tag_name.name
                            for tag_name in [
                                Tag.explanation_node,
                                Tag.retrieval_progress_node,
                            ]
                        ]
                        for tag in tags
                    ):
                        list_data = event["data"]["output"].split(" ")
                        for token in list_data:
                            yield {
                                "type": "token",
                                "delta": token + " ",
                            }
                            await asyncio.sleep(0.01)
                    elif any(
                        tag in [tag_name.name for tag_name in [Tag.direct_response_node]]
                        for tag in tags
                    ):
                        list_data = event["data"]["output"].split(" ")
                        for token in list_data:
                            yield {
                                "type": "token",
                                "delta": token + " ",
                            }
                            await asyncio.sleep(0.005)
                    else:
                        yield {
                            "type": "token",
                            "delta": event["data"]["output"],
                        }

                if kind == "on_chat_model_stream" and "streaming_node" in tags:
                    yield {
                        "type": "token",
                        "delta": event["data"]["chunk"].content,
                    }

                if kind == "on_custom_event" and event.get("name") == "status":
                    msg = event["data"].get("message", "")
                    if msg:
                        yield {
                            "type": "status",
                            "step": event["data"].get("step"),
                            "message": msg,
                        }
        finally:
            del graph
