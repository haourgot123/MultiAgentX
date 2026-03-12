from __future__ import annotations

import json
from pathlib import Path

from loguru import logger
from openai import OpenAI
from sqlalchemy.orm import Session

from backend.api.data_ingestion.extraction import extract_service
from backend.api.data_ingestion.model import (
    ExtractedTextBlock,
    IngestionChunk,
    IngestionRunResponse,
    IngestionStatus,
)
from backend.api.files.model import StoredFile
from backend.config.settings import _settings
from backend.databases.db import SessionLocal, get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message


class DataIngestionService:
    def __init__(self):
        self.chunk_size = max(_settings.chunk.chunk_size, 200)
        self.chunk_overlap = max(0, min(_settings.chunk.chunk_overlap, self.chunk_size - 1))
        self.embedding_model = _settings.openai_embedding.embedding_model
        self.embedding_batch_size = max(1, _settings.openai_embedding.batch_size)
        self.embedding_dimension = _settings.openai_embedding.embedding_dimension
        self.collection_name = _settings.milvus.collection_name

    @staticmethod
    def _truncate(value: str | None, max_len: int = 1000) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) <= max_len:
            return normalized
        return normalized[: max_len - 3] + "..."

    def _get_user_file(self, db_session: Session, user_id: int, file_id: int) -> StoredFile:
        stored_file = (
            db_session.query(StoredFile)
            .filter(StoredFile.id == file_id, StoredFile.user_id == user_id)
            .first()
        )
        if not stored_file:
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return stored_file

    @staticmethod
    def _set_file_status(
        db_session: Session,
        stored_file: StoredFile,
        status: IngestionStatus,
        *,
        error: str | None = None,
        chunks: int | None = None,
        ingested: bool = False,
    ) -> None:
        stored_file.ingestion_status = status.value
        stored_file.ingestion_error = error
        if chunks is not None:
            stored_file.ingested_chunks = chunks
        stored_file.ingested_at = get_utc_now() if ingested else None
        stored_file.updated_at = get_utc_now()
        db_session.add(stored_file)
        db_session.commit()
        db_session.refresh(stored_file)

    def _build_chunks(self, text_blocks: list[ExtractedTextBlock]) -> list[IngestionChunk]:
        if not text_blocks:
            return []

        normalized_blocks: list[ExtractedTextBlock] = []
        for block in text_blocks:
            clean_text = block.text.strip()
            if not clean_text:
                continue

            if len(clean_text) <= self.chunk_size:
                normalized_blocks.append(
                    ExtractedTextBlock(
                        text=clean_text,
                        page_no=block.page_no,
                        bbox=block.bbox,
                        metadata=block.metadata,
                    )
                )
                continue

            cursor = 0
            while cursor < len(clean_text):
                piece = clean_text[cursor : cursor + self.chunk_size]
                normalized_blocks.append(
                    ExtractedTextBlock(
                        text=piece,
                        page_no=block.page_no,
                        bbox=block.bbox,
                        metadata=block.metadata,
                    )
                )
                cursor += self.chunk_size

        chunks: list[IngestionChunk] = []
        window_blocks: list[ExtractedTextBlock] = []
        window_size = 0

        def _finalize_chunk(index: int, blocks: list[ExtractedTextBlock]) -> IngestionChunk:
            bboxes = []
            for source_block in blocks:
                if source_block.bbox is None:
                    continue
                bboxes.append(
                    {
                        "page_no": source_block.page_no,
                        "bbox": source_block.bbox,
                    }
                )

            return IngestionChunk(
                chunk_index=index,
                text="\n".join(block.text for block in blocks).strip(),
                page_no=next((block.page_no for block in blocks if block.page_no is not None), None),
                bboxes=bboxes,
            )

        for block in normalized_blocks:
            projected = window_size + len(block.text) + 1
            if window_blocks and projected > self.chunk_size:
                chunks.append(_finalize_chunk(len(chunks), window_blocks))

                if self.chunk_overlap > 0:
                    overlap_blocks: list[ExtractedTextBlock] = []
                    overlap_size = 0
                    for previous in reversed(window_blocks):
                        previous_size = len(previous.text) + 1
                        if overlap_blocks and overlap_size + previous_size > self.chunk_overlap:
                            break
                        overlap_blocks.insert(0, previous)
                        overlap_size += previous_size

                    window_blocks = overlap_blocks
                    window_size = overlap_size
                else:
                    window_blocks = []
                    window_size = 0

            window_blocks.append(block)
            window_size += len(block.text) + 1

        if window_blocks:
            chunks.append(_finalize_chunk(len(chunks), window_blocks))

        return [chunk for chunk in chunks if chunk.text]

    def _embed_chunks(self, chunks: list[IngestionChunk]) -> list[list[float]]:
        if not chunks:
            return []

        api_key = _settings.openai_embedding.api_key
        if not api_key:
            raise InvalidRequestException(
                message="Missing OPENAI_API_KEY for embedding generation"
            )

        client = OpenAI(
            api_key=api_key,
            base_url=_settings.openai_embedding.api_base,
            timeout=_settings.openai_embedding.timeout_seconds,
        )

        vectors: list[list[float]] = []
        for offset in range(0, len(chunks), self.embedding_batch_size):
            batch = chunks[offset : offset + self.embedding_batch_size]
            response = client.embeddings.create(
                model=self.embedding_model,
                input=[chunk.text for chunk in batch],
            )
            vectors.extend([item.embedding for item in response.data])

        if len(vectors) != len(chunks):
            raise InvalidRequestException(
                message="Embedding output size does not match number of chunks"
            )

        if vectors and len(vectors[0]) != self.embedding_dimension:
            raise InvalidRequestException(
                message=(
                    f"Embedding dimension mismatch: expected {self.embedding_dimension}, "
                    f"received {len(vectors[0])}"
                )
            )

        return vectors

    def _get_milvus_collection(self):
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )
        except ModuleNotFoundError as exc:
            raise InvalidRequestException(
                message="Milvus client is not installed. Please install `pymilvus`."
            ) from exc

        connect_kwargs = {
            "host": _settings.milvus.host,
            "port": _settings.milvus.port,
        }
        if _settings.milvus.user:
            connect_kwargs["user"] = _settings.milvus.user
        if _settings.milvus.password:
            connect_kwargs["password"] = _settings.milvus.password

        connections.connect(alias="default", **connect_kwargs)

        if not utility.has_collection(self.collection_name):
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=128,
                    is_primary=True,
                    auto_id=False,
                ),
                FieldSchema(name="user_id", dtype=DataType.INT64),
                FieldSchema(name="file_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="page_no", dtype=DataType.INT64),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="bbox", dtype=DataType.VARCHAR, max_length=16384),
                FieldSchema(name="created_unix", dtype=DataType.INT64),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.embedding_dimension,
                ),
            ]
            schema = CollectionSchema(
                fields=fields,
                description="RAG chunks generated from uploaded files",
                enable_dynamic_field=False,
            )
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                consistency_level=_settings.milvus.consistency_level,
            )
            collection.create_index(
                field_name="vector",
                index_params={
                    "metric_type": _settings.milvus.metric_type,
                    "index_type": _settings.milvus.index_type,
                    "params": {"nlist": _settings.milvus.nlist},
                },
            )
        else:
            collection = Collection(self.collection_name)
            if not collection.indexes:
                collection.create_index(
                    field_name="vector",
                    index_params={
                        "metric_type": _settings.milvus.metric_type,
                        "index_type": _settings.milvus.index_type,
                        "params": {"nlist": _settings.milvus.nlist},
                    },
                )

        collection.load()
        return collection

    @staticmethod
    def _serialize_bbox_payload(chunk: IngestionChunk) -> str:
        payload = chunk.bboxes
        serialized = json.dumps(payload, ensure_ascii=False)
        if len(serialized) <= 16000:
            return serialized

        trimmed_payload = payload[:40]
        return json.dumps(
            {
                "truncated": True,
                "sample": trimmed_payload,
                "total": len(payload),
            },
            ensure_ascii=False,
        )

    def _upsert_chunks(
        self,
        *,
        user_id: int,
        stored_file: StoredFile,
        chunks: list[IngestionChunk],
        vectors: list[list[float]],
    ) -> None:
        collection = self._get_milvus_collection()
        delete_expr = f"user_id == {user_id} and file_id == {stored_file.id}"
        try:
            collection.delete(expr=delete_expr)
        except Exception as exc:
            logger.warning(
                "Milvus delete before upsert failed for file_id={} user_id={}: {}",
                stored_file.id,
                user_id,
                exc,
            )

        now_unix = int(get_utc_now().timestamp())
        ids = [f"{user_id}:{stored_file.id}:{chunk.chunk_index}" for chunk in chunks]
        rows = [
            ids,
            [user_id] * len(chunks),
            [stored_file.id] * len(chunks),
            [chunk.chunk_index for chunk in chunks],
            [chunk.page_no if chunk.page_no is not None else -1 for chunk in chunks],
            [chunk.text[:65535] for chunk in chunks],
            [self._serialize_bbox_payload(chunk) for chunk in chunks],
            [now_unix] * len(chunks),
            vectors,
        ]

        collection.insert(rows)
        collection.flush()

    def _run_ingestion_pipeline(self, stored_file: StoredFile) -> tuple[int, str | None]:
        path = Path(stored_file.storage_path)
        if not path.exists():
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)

        blocks = extract_service.extract_text_blocks(path)
        chunks = self._build_chunks(blocks)
        if not chunks:
            raise InvalidRequestException(message="No text extracted for ingestion")

        vectors = self._embed_chunks(chunks)
        self._upsert_chunks(
            user_id=stored_file.user_id,
            stored_file=stored_file,
            chunks=chunks,
            vectors=vectors,
        )
        return len(chunks), None

    def ingest_file(self, db_session: Session, user_id: int, file_id: int) -> IngestionRunResponse:
        stored_file = self._get_user_file(db_session, user_id, file_id)
        self._set_file_status(
            db_session,
            stored_file,
            IngestionStatus.PROCESSING,
            error=None,
            chunks=0,
            ingested=False,
        )

        try:
            chunk_count, _ = self._run_ingestion_pipeline(stored_file)
            self._set_file_status(
                db_session,
                stored_file,
                IngestionStatus.COMPLETED,
                error=None,
                chunks=chunk_count,
                ingested=True,
            )
        except Exception as exc:
            logger.exception("Ingestion failed for file_id={} user_id={}", file_id, user_id)
            self._set_file_status(
                db_session,
                stored_file,
                IngestionStatus.FAILED,
                error=self._truncate(str(exc), 1000),
                chunks=0,
                ingested=False,
            )

        return IngestionRunResponse(
            file_id=stored_file.id,
            status=stored_file.ingestion_status,
            chunks=stored_file.ingested_chunks,
            error=stored_file.ingestion_error,
        )

    def ingest_files(
        self,
        db_session: Session,
        user_id: int,
        file_ids: list[int],
    ) -> list[IngestionRunResponse]:
        results: list[IngestionRunResponse] = []
        for file_id in file_ids:
            results.append(self.ingest_file(db_session, user_id, file_id))
        return results

    def ingest_file_by_id(self, user_id: int, file_id: int) -> None:
        db_session = SessionLocal()
        try:
            self.ingest_file(db_session, user_id, file_id)
        except Exception:
            logger.exception(
                "Background ingestion encountered unexpected failure for file_id={} user_id={}",
                file_id,
                user_id,
            )
        finally:
            db_session.close()

    def get_ingestion_status(
        self, db_session: Session, user_id: int, file_id: int
    ) -> StoredFile:
        return self._get_user_file(db_session, user_id, file_id)

    def delete_file_vectors(self, user_id: int, file_id: int) -> None:
        try:
            collection = self._get_milvus_collection()
            collection.delete(expr=f"user_id == {user_id} and file_id == {file_id}")
            collection.flush()
        except Exception as exc:
            logger.warning(
                "Skip vector cleanup for file_id={} user_id={} because Milvus is unavailable: {}",
                file_id,
                user_id,
                exc,
            )


data_ingestion_service = DataIngestionService()
