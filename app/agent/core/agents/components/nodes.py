"""
Agent Nodes Module

This module provides reusable node functions for LangGraph workflows.
Nodes represent individual steps in the agent execution graph.
"""

from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough


class AgentNodes:
    """
    Collection of reusable node functions for agent workflows.

    These nodes can be composed to create complex agent behaviors.
    """

    @staticmethod
    def create_llm_call_node(llm: Any, system_prompt: Optional[str] = None):
        """
        Create a node that calls an LLM.

        Args:
            llm: Language model instance
            system_prompt: Optional system prompt to prepend

        Returns:
            Node function that calls the LLM
        """
        def llm_call_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Call LLM with messages from state."""
            messages = state.get("messages", [])

            # Add system prompt if provided
            if system_prompt and (not messages or not isinstance(messages[0], SystemMessage)):
                messages = [SystemMessage(content=system_prompt)] + messages

            # Call LLM
            response = llm.invoke(messages)

            # Return updated state
            return {
                "messages": [response]
            }

        return llm_call_node

    @staticmethod
    def create_retrieval_node(retriever: Any):
        """
        Create a node that retrieves relevant documents.

        Args:
            retriever: Retriever instance (e.g., from vector database)

        Returns:
            Node function that performs retrieval
        """
        def retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Retrieve relevant documents based on query."""
            query = state.get("question") or state.get("query", "")

            # Retrieve documents
            docs = retriever.invoke(query)

            # Format context
            context = "\n\n".join([doc.page_content for doc in docs])

            # Extract sources
            sources = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ]

            return {
                "context": context,
                "sources": sources
            }

        return retrieval_node

    @staticmethod
    def create_answer_generation_node(llm: Any, prompt_template: Optional[str] = None):
        """
        Create a node that generates an answer based on context.

        Args:
            llm: Language model instance
            prompt_template: Optional custom prompt template

        Returns:
            Node function that generates answers
        """
        default_template = """You are a helpful assistant. Answer the question based on the provided context.

Context:
{context}

Question: {question}

Provide a clear and concise answer based only on the given context. If the context doesn't contain enough information, say so."""

        template = prompt_template or default_template
        prompt = ChatPromptTemplate.from_template(template)

        def answer_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Generate answer using LLM."""
            question = state.get("question", "")
            context = state.get("context", "")

            # Generate answer
            chain = prompt | llm
            response = chain.invoke({
                "question": question,
                "context": context
            })

            # Extract answer text
            answer = response.content if hasattr(response, "content") else str(response)

            return {
                "answer": answer,
                "messages": [AIMessage(content=answer)]
            }

        return answer_generation_node

    @staticmethod
    def create_tool_execution_node(tools: List[Any]):
        """
        Create a node that executes tools based on LLM decisions.

        Args:
            tools: List of tool instances

        Returns:
            Node function that executes tools
        """
        # Create tool map
        tool_map = {tool.name: tool for tool in tools}

        def tool_execution_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Execute the specified tool."""
            tool_name = state.get("tool_name")
            tool_input = state.get("tool_input", {})

            if not tool_name or tool_name not in tool_map:
                return {
                    "tool_error": f"Tool '{tool_name}' not found",
                    "should_continue": False
                }

            try:
                # Execute tool
                tool = tool_map[tool_name]
                result = tool.invoke(tool_input)

                return {
                    "tool_output": result,
                    "tool_error": None,
                    "should_continue": True
                }
            except Exception as e:
                return {
                    "tool_error": str(e),
                    "should_continue": False
                }

        return tool_execution_node

    @staticmethod
    def create_routing_node(condition_func):
        """
        Create a conditional routing node.

        Args:
            condition_func: Function that takes state and returns next node name

        Returns:
            Node function that performs routing
        """
        def routing_node(state: Dict[str, Any]) -> str:
            """Route to next node based on condition."""
            return condition_func(state)

        return routing_node

    @staticmethod
    def create_format_output_node(output_format: Optional[Dict[str, str]] = None):
        """
        Create a node that formats the final output.

        Args:
            output_format: Dictionary mapping state keys to output keys

        Returns:
            Node function that formats output
        """
        def format_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Format the output according to specification."""
            if not output_format:
                return state

            formatted = {}
            for state_key, output_key in output_format.items():
                if state_key in state:
                    formatted[output_key] = state[state_key]

            return formatted

        return format_output_node

    @staticmethod
    def create_history_management_node(max_history: int = 10):
        """
        Create a node that manages conversation history.

        Args:
            max_history: Maximum number of messages to keep

        Returns:
            Node function that manages history
        """
        def history_management_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Manage conversation history."""
            messages = state.get("messages", [])

            # Keep only recent messages
            if len(messages) > max_history:
                # Keep system message if present
                system_messages = [m for m in messages if isinstance(m, SystemMessage)]
                other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

                # Keep recent messages
                recent_messages = other_messages[-max_history:]
                messages = system_messages + recent_messages

            return {"messages": messages}

        return history_management_node

    @staticmethod
    def create_validation_node(validation_func):
        """
        Create a node that validates state.

        Args:
            validation_func: Function that takes state and returns (bool, error_message)

        Returns:
            Node function that validates state
        """
        def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Validate the current state."""
            is_valid, error_msg = validation_func(state)

            if not is_valid:
                return {
                    "error": error_msg,
                    "is_valid": False
                }

            return {"is_valid": True}

        return validation_node


# Utility functions for common routing conditions
def should_continue_research(state: Dict[str, Any]) -> str:
    """Determine if research should continue."""
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)

    if iteration >= max_iterations:
        return "finalize"
    return "continue"


def should_execute_tool(state: Dict[str, Any]) -> str:
    """Determine if a tool should be executed."""
    messages = state.get("messages", [])

    if not messages:
        return "end"

    last_message = messages[-1]

    # Check if last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"

    return "end"


def route_by_intent(state: Dict[str, Any]) -> str:
    """Route based on detected intent."""
    intent = state.get("current_intent", "general")

    intent_routing = {
        "question": "answer_question",
        "research": "do_research",
        "general": "general_chat",
    }

    return intent_routing.get(intent, "general_chat")
