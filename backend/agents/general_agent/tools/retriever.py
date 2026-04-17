import json
from typing import List, Optional
from loguru import logger
from openai import AzureOpenAI
from pydantic import BaseModel
from pymilvus import Collection, connections, AsyncMilvusClient

from backend.config.settings import _settings


service_logger = logger.bind(service="retriever-service")


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float = 0.0
    file_name: str = ""
    file_id: int = 0
    page_no: Optional[int] = None
    chunk_index: int = 0
    bbox_json: str = ""
    metadata: dict = {}


class HybridSearchResult(BaseModel):
    query: str
    vector_results: List[RetrievedChunk] = []
    bm25_results: List[RetrievedChunk] = []
    merged_results: List[RetrievedChunk] = []


class RetrieverConfig(BaseModel):
    vector_top_k: int = 10
    bm25_top_k: int = 10
    hybrid_alpha: float = 0.7
    rerank_top_n: int = 5


class HybridRetriever:
    def __init__(self, config: Optional[RetrieverConfig] = None):
        self.config = config or RetrieverConfig()
        self.collection_name = _settings.milvus.collection_name
        self._embedding_client = None
        self._collection = None
        self._available_fields = None

    def _get_embedding_client(self) -> AzureOpenAI:
        if self._embedding_client is None:
            api_key = _settings.openai_embedding.api_key
            if _settings.openai_embedding.endpoint:
                self._embedding_client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=_settings.openai_embedding.endpoint,
                    api_version=_settings.openai_embedding.api_version,
                    timeout=_settings.openai_embedding.timeout_seconds,
                )
            else:
                from openai import OpenAI
                self._embedding_client = OpenAI(
                    api_key=api_key,
                    base_url=_settings.openai_embedding.api_base,
                    timeout=_settings.openai_embedding.timeout_seconds,
                )
        return self._embedding_client

    def _get_collection(self) -> Collection:
        # Ensure Milvus connection is alive (reconnect if dropped)
        connect_kwargs = {
            "host": _settings.milvus.host,
            "port": _settings.milvus.port,
        }
        if _settings.milvus.user:
            connect_kwargs["user"] = _settings.milvus.user
        if _settings.milvus.password:
            connect_kwargs["password"] = _settings.milvus.password

        try:
            # Check if connection is still alive
            if not connections.has_connection("default"):
                connections.connect(alias="default", **connect_kwargs)
            else:
                # Verify connection is actually working
                from pymilvus import utility
                utility.list_collections(using="default")
        except Exception:
            # Connection lost — reconnect
            try:
                connections.disconnect("default")
            except Exception:
                pass
            connections.connect(alias="default", **connect_kwargs)
            self._collection = None  # Force collection refresh

        if self._collection is None:
            self._collection = Collection(self.collection_name, using="default")
            self._collection.load()
        return self._collection

    def _generate_embedding(self, text: str) -> List[float]:
        client = self._get_embedding_client()
        response = client.embeddings.create(
            model=_settings.openai_embedding.embedding_model,
            input=[text],
        )
        return response.data[0].embedding

    def _get_available_output_fields(self) -> List[str]:
        """Detect which output fields actually exist in the collection schema."""
        if self._available_fields is not None:
            return self._available_fields

        collection = self._get_collection()
        schema_fields = {f.name for f in collection.schema.fields}

        # Desired fields in priority order
        desired = ["id", "text", "file_name", "file_id", "page_no", "chunk_index", "bbox", "metadata_json"]
        self._available_fields = [f for f in desired if f in schema_fields]

        service_logger.info(
            f"Collection '{self.collection_name}' available fields: {self._available_fields} "
            f"(schema has {len(schema_fields)} fields total)"
        )
        return self._available_fields

    def _vector_search(
        self,
        query_embedding: List[float],
        user_id: int,
        file_ids: Optional[List[int]] = None,
        top_k: int = 10,
    ) -> List[RetrievedChunk]:
        collection = self._get_collection()
        
        expr = f"user_id == {user_id}"
        if file_ids:
            file_ids_str = ", ".join(str(fid) for fid in file_ids)
            expr += f" and file_id in [{file_ids_str}]"

        search_params = {
            "metric_type": _settings.milvus.metric_type,
            "params": {"nprobe": 128},
        }

        results = collection.search(
            data=[query_embedding],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=self._get_available_output_fields(),
        )

        chunks = []
        if results and len(results) > 0:
            for hit in results[0]:
                chunk = RetrievedChunk(
                    chunk_id=str(hit.id),
                    text=hit.entity.get("text", ""),
                    score=float(hit.score),
                    file_name=hit.entity.get("file_name", ""),
                    file_id=int(hit.entity.get("file_id", 0)),
                    page_no=hit.entity.get("page_no"),
                    chunk_index=int(hit.entity.get("chunk_index", 0)),
                    bbox_json=hit.entity.get("bbox", "") or "",
                    metadata=self._parse_metadata(hit.entity.get("metadata_json")),
                )
                chunks.append(chunk)
        
        return chunks

    def _bm25_search(
        self,
        query: str,
        user_id: int,
        file_ids: Optional[List[int]] = None,
        top_k: int = 10,
    ) -> List[RetrievedChunk]:
        collection = self._get_collection()
        
        keywords = [kw.strip().lower() for kw in query.split() if len(kw.strip()) > 1]
        if not keywords:
            return []

        expr = f"user_id == {user_id}"
        if file_ids:
            file_ids_str = ", ".join(str(fid) for fid in file_ids)
            expr += f" and file_id in [{file_ids_str}]"

        text_match_expr = " || ".join([f'text like "%{kw}%"' for kw in keywords[:5]])
        full_expr = f"({expr}) and ({text_match_expr})"

        try:
            results = collection.query(
                expr=full_expr,
                output_fields=self._get_available_output_fields(),
                limit=top_k,
            )

            chunks = []
            for row in results:
                text = row.get("text", "")
                score = sum(1 for kw in keywords if kw in text.lower()) / max(len(keywords), 1)
                chunk = RetrievedChunk(
                    chunk_id=str(row.get("id", "")),
                    text=text,
                    score=score,
                    file_name=row.get("file_name", ""),
                    file_id=int(row.get("file_id", 0)),
                    page_no=row.get("page_no"),
                    chunk_index=int(row.get("chunk_index", 0)),
                    bbox_json=row.get("bbox", "") or "",
                    metadata=self._parse_metadata(row.get("metadata_json")),
                )
                chunks.append(chunk)
            
            chunks.sort(key=lambda x: x.score, reverse=True)
            return chunks[:top_k]
        except Exception as e:
            service_logger.warning(f"BM25 search failed: {e}")
            return []

    def _parse_metadata(self, metadata_json: Optional[str]) -> dict:
        if not metadata_json:
            return {}
        try:
            return json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
        except (json.JSONDecodeError, TypeError):
            return {}

    def _merge_results(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        alpha: float = 0.7,
    ) -> List[RetrievedChunk]:
        chunk_scores = {}
        
        max_vector_score = max((c.score for c in vector_results), default=1.0)
        for chunk in vector_results:
            normalized_score = chunk.score / max_vector_score if max_vector_score > 0 else 0
            chunk_scores[chunk.chunk_id] = {
                "chunk": chunk,
                "vector_score": normalized_score,
                "bm25_score": 0.0,
            }

        max_bm25_score = max((c.score for c in bm25_results), default=1.0)
        for chunk in bm25_results:
            normalized_score = chunk.score / max_bm25_score if max_bm25_score > 0 else 0
            if chunk.chunk_id in chunk_scores:
                chunk_scores[chunk.chunk_id]["bm25_score"] = normalized_score
            else:
                chunk_scores[chunk.chunk_id] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "bm25_score": normalized_score,
                }

        merged = []
        for chunk_id, scores in chunk_scores.items():
            combined_score = (
                alpha * scores["vector_score"] + (1 - alpha) * scores["bm25_score"]
            )
            chunk = scores["chunk"].model_copy()
            chunk.score = combined_score
            merged.append(chunk)

        merged.sort(key=lambda x: x.score, reverse=True)
        return merged

    async def search(
        self,
        query: str,
        user_id: int,
        file_ids: Optional[List[int]] = None,
    ) -> HybridSearchResult:
        service_logger.info(f"Hybrid search for user_id={user_id}, query='{query[:50]}...'")

        query_embedding = self._generate_embedding(query)

        vector_results = self._vector_search(
            query_embedding=query_embedding,
            user_id=user_id,
            file_ids=file_ids,
            top_k=self.config.vector_top_k,
        )
        service_logger.debug(f"Vector search returned {len(vector_results)} results")

        bm25_results = self._bm25_search(
            query=query,
            user_id=user_id,
            file_ids=file_ids,
            top_k=self.config.bm25_top_k,
        )
        service_logger.debug(f"BM25 search returned {len(bm25_results)} results")

        merged_results = self._merge_results(
            vector_results=vector_results,
            bm25_results=bm25_results,
            alpha=self.config.hybrid_alpha,
        )
        merged_results = merged_results[:self.config.rerank_top_n]

        return HybridSearchResult(
            query=query,
            vector_results=vector_results,
            bm25_results=bm25_results,
            merged_results=merged_results,
        )

    def close(self):
        try:
            connections.disconnect("default")
        except Exception:
            pass


hybrid_retriever = HybridRetriever()