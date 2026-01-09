from typing import Any, Callable, Dict

from qdrant_client import AsyncQdrantClient, QdrantClient

from backend.config.settings import _settings


class VectorDBFactory:
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, creator: Callable[[], Any]):
        cls._registry[name] = creator

    @classmethod
    def create_resource(cls, name: str) -> Any:
        creator = cls._registry.get(name)
        if not creator:
            raise ValueError(f"No resource named '{name}' registered.")
        return creator()

    @classmethod
    def register_qdrant(cls):
        return QdrantClient(
            url=_settings.qdrant.qdrant_url, timeout=_settings.qdrant.qdrant_timeout
        )

    @classmethod
    def register_async_qdrant(cls):
        return AsyncQdrantClient(
            url=_settings.qdrant.qdrant_url, timeout=_settings.qdrant.qdrant_timeout
        )


VectorDBFactory.register("qdrant", VectorDBFactory.register_qdrant)
VectorDBFactory.register("async_qdrant", VectorDBFactory.register_async_qdrant)
