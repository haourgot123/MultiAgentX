from datetime import datetime
from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger
from backend.agents.general_agent.state import GeneralAgentState
from langchain_core.messages import HumanMessage, AIMessage
from backend.memory.mem0_client import mem0_client
from typing import List, Dict, Any


class MemoryNode(Runnable):
    def __init__(self) -> None:
        """Initialize the MemoryNode with Mem0 integration."""
        super().__init__()
        self.logger = logger.bind(service="memory-node")

    def invoke(self, state: GeneralAgentState, **kwargs):
        pass

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        """Load both short-term (conversation) and long-term (Mem0) memories."""
        dispatch_custom_event(
            "status",
            {"step": "memory", "message": "🧠 Loading conversation context..."},
        )

        # 1. Format short-term conversation messages
        langchain_memories = []
        memory_count = 0
        if state.memories:
            memory_count = len(state.memories)
            for i, message in enumerate(state.memories):
                if message.role == "user":
                    langchain_memories.append(HumanMessage(content=message.content))
                elif message.role == "assistant":
                    langchain_memories.append(AIMessage(content=message.content))

        # 2. Retrieve long-term memories from Mem0 (Milvus)
        long_term_memory_context = ""
        try:
            dispatch_custom_event(
                "status",
                {"step": "memory", "message": "📚 Searching long-term memories..."},
            )
            
            user_id = str(state.user_id)
            
            # Search for relevant memories based on user question
            mem0_memories = await mem0_client.search_memories(
                query=state.user_question,
                user_id=user_id,
                limit=5  # Get top 5 relevant memories
            )
            
            if mem0_memories:
                # Format long-term memories as context
                long_term_memory_context = "\n\n--- Long-term Memories ---\n"
                for idx, mem in enumerate(mem0_memories, 1):
                    memory_text = mem.get("memory", "")
                    score = mem.get("score", 0)
                    long_term_memory_context += f"{idx}. {memory_text} (relevance: {score:.2f})\n"
                    self.logger.debug(f"Retrieved memory {idx}: {memory_text[:100]}")
                
                dispatch_custom_event(
                    "status",
                    {"step": "memory", "message": f"✅ Found {len(mem0_memories)} long-term memories."},
                )
            else:
                dispatch_custom_event(
                    "status",
                    {"step": "memory", "message": "ℹ️ No long-term memories found."},
                )
                
        except Exception as e:
            self.logger.error(f"Error retrieving long-term memories: {e}")
            # Graceful degradation - continue without long-term memories
            dispatch_custom_event(
                "status",
                {"step": "memory", "message": "⚠️ Long-term memory unavailable, using short-term only."},
            )

        # 3. Prepare result for next node
        result = {
            "memories": langchain_memories,
            "long_term_memory_context": long_term_memory_context,
        }
        
        dispatch_custom_event(
            "status",
            {"step": "memory", "message": f"✅ Loaded {memory_count} conversation messages."},
        )

        return result
