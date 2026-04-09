from typing import List, Dict, Any, Optional
from mem0 import AsyncMemory
from backend.config.settings import _settings
from loguru import logger
import os


class Mem0Client:
    """
    Async wrapper for Mem0 long-term memory operations.
    Uses Azure OpenAI for LLM and embeddings.
    Uses Milvus for vector storage (reuse existing infrastructure).
    """
    
    def __init__(self):
        self._memory: Optional[AsyncMemory] = None
        self.logger = logger.bind(service="mem0-client")
        self._initialized = False
    
    async def initialize(self):
        """Lazy initialization of AsyncMemory instance."""
        if self._initialized:
            return
        
        if not _settings.mem0.enable_long_term_memory:
            self.logger.warning("Mem0 long-term memory is disabled")
            return
        
        try:
            config = self._build_config()
            self._memory = AsyncMemory.from_config(config)
            self._initialized = True
            self.logger.info("Mem0 AsyncMemory client initialized successfully with Milvus")
        except Exception as e:
            self.logger.error(f"Failed to initialize Mem0 client: {e}")
            raise
    
    def _build_config(self) -> Dict[str, Any]:
        """
        Build Mem0 configuration dictionary.
        Reuses existing Milvus + Azure OpenAI configs.
        """
        # Set environment variables for Mem0 (required by mem0ai package)
        # LLM config (Azure OpenAI GPT-5.1)
        os.environ["LLM_AZURE_OPENAI_API_KEY"] = _settings.azure_chat_openai.api_key
        os.environ["LLM_AZURE_DEPLOYMENT"] = _settings.azure_chat_openai.deployment_name_gpt_5_1
        os.environ["LLM_AZURE_ENDPOINT"] = _settings.azure_chat_openai.api_endpoint
        os.environ["LLM_AZURE_API_VERSION"] = _settings.azure_chat_openai.api_version
        
        # Embedder config (Azure OpenAI text-embedding-3-large)
        os.environ["EMBEDDING_AZURE_OPENAI_API_KEY"] = _settings.openai_embedding.api_key
        os.environ["EMBEDDING_AZURE_DEPLOYMENT"] = _settings.openai_embedding.embedding_model
        os.environ["EMBEDDING_AZURE_ENDPOINT"] = _settings.openai_embedding.endpoint
        os.environ["EMBEDDING_AZURE_API_VERSION"] = _settings.openai_embedding.api_version
        
        config = {
            "vector_store": {
                "provider": "milvus",
                "config": {
                    "collection_name": _settings.mem0.memory_collection_name,
                    "url": f"http://{_settings.mem0.milvus_host}:{_settings.mem0.milvus_port}",
                    "embedding_model_dims": _settings.mem0.embedding_dims,
                }
            },
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "model": _settings.azure_chat_openai.deployment_name_gpt_5_1,
                    "temperature": _settings.azure_chat_openai.temperature,
                    "azure_kwargs": {
                        "api_version": _settings.azure_chat_openai.api_version,
                        "azure_deployment": _settings.azure_chat_openai.deployment_name_gpt_5_1,
                        "azure_endpoint": _settings.azure_chat_openai.api_endpoint,
                        "api_key": _settings.azure_chat_openai.api_key,
                    }
                }
            },
            "embedder": {
                "provider": "azure_openai",
                "config": {
                    "model": _settings.openai_embedding.embedding_model,
                    "embedding_dims": _settings.mem0.embedding_dims,
                    "azure_kwargs": {
                        "api_version": _settings.openai_embedding.api_version,
                        "azure_deployment": _settings.openai_embedding.embedding_model,
                        "azure_endpoint": _settings.openai_embedding.endpoint,
                        "api_key": _settings.openai_embedding.api_key,
                    }
                }
            },
            "history_db_path": _settings.mem0.history_db_path,
        }
        
        return config
    
    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add memories from conversation messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier for entity-scoped memory
            metadata: Optional metadata (conversation_id, timestamp, etc.)
        
        Returns:
            Dict with results or None if disabled/failed
        """
        if not self._initialized or not self._memory:
            self.logger.debug("Mem0 not initialized or disabled, skipping add_memory")
            return None
        
        try:
            self.logger.debug(
                f"Adding memory for user_id={user_id}, messages_count={len(messages)}"
            )
            
            result = await self._memory.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata or {},
                infer=True
            )
            
            results = result.get("results", [])
            self.logger.info(
                f"Successfully stored {len(results)} memories in Milvus for user {user_id}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding memory: {e}")
            return None
    
    async def search_memories(
        self,
        query: str,
        user_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search relevant memories for a user from Milvus.
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum number of results
        
        Returns:
            List of relevant memory objects
        """
        if not self._initialized or not self._memory:
            self.logger.debug("Mem0 not initialized or disabled, returning empty memories")
            return []
        
        try:
            limit = limit or _settings.mem0.memory_top_k
            
            result = await self._memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )
            
            memories = result.get("results", [])
            
            filtered_memories = [
                mem for mem in memories 
                if mem.get("score", 0) >= _settings.mem0.memory_score_threshold
            ]
            
            self.logger.debug(
                f"Found {len(filtered_memories)}/{len(memories)} relevant memories "
                f"for user {user_id} (threshold={_settings.mem0.memory_score_threshold})"
            )
            
            return filtered_memories
            
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            return []
    
    async def get_all_memories(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        if not self._initialized or not self._memory:
            return []
        
        try:
            result = await self._memory.get_all(
                user_id=user_id,
                limit=limit,
            )
            
            memories = result.get("results", [])
            self.logger.debug(f"Retrieved {len(memories)} memories for user {user_id}")
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Error getting all memories: {e}")
            return []
    
    async def delete_memory(
        self,
        memory_id: str,
    ) -> bool:
        """Delete a specific memory by ID."""
        if not self._initialized or not self._memory:
            return False
        
        try:
            await self._memory.delete(memory_id=memory_id)
            self.logger.info(f"Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    async def clear_user_memories(
        self,
        user_id: str,
    ) -> bool:
        """Clear all memories for a user."""
        if not self._initialized or not self._memory:
            return False
        
        try:
            await self._memory.delete_all(user_id=user_id)
            self.logger.info(f"Cleared all memories for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing memories for user {user_id}: {e}")
            return False


# Singleton instance
mem0_client = Mem0Client()