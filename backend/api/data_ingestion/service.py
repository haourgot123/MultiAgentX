from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from openai import AzureOpenAI, OpenAI
from sqlalchemy.orm import Session
from fastapi import Request
from backend.api.data_ingestion.extraction import extract_service
from backend.api.data_ingestion.model import (
    ExtractedTextBlock,
    IngestionChunk,
    IngestionPipelineStatus,
    IngestionRunResponse,
    IngestionStatus,
)
from backend.api.files.model import StoredFile
from backend.config.settings import _settings
from backend.databases.db import SessionLocal, get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.realtime.socketio import socketio_manager
from backend.utils.constants import Message

service_logger = logger.bind(service="ingestion-service")


class DataIngestionService:
    def __init__(self):
        self.chunk_size = max(_settings.chunk.chunk_size, 200)
        self.chunk_overlap = max(0, min(_settings.chunk.chunk_overlap, self.chunk_size - 1))
        self.embedding_model = _settings.openai_embedding.embedding_model
        self.embedding_batch_size = max(1, _settings.openai_embedding.batch_size)
        self.embedding_dimension = _settings.openai_embedding.embedding_dimension
        self.embedding_endpoint = _settings.openai_embedding.endpoint
        self.embedding_api_version = _settings.openai_embedding.api_version
        self.collection_name = _settings.milvus.collection_name

    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return service_logger.bind(
            request_id=getattr(getattr(request, "state", None), "request_id", "-"),
            user_id=user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-"),
        )

    @staticmethod
    def _truncate(value: str | None, max_len: int = 1000) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) <= max_len:
            return normalized
        return normalized[: max_len - 3] + "..."

    def _get_user_file(
        self,
        db_session: Session,
        user_id: int,
        file_id: int,
        request_logger,
    ) -> StoredFile:
        stored_file = (
            db_session.query(StoredFile)
            .filter(StoredFile.id == file_id, StoredFile.user_id == user_id)
            .first()
        )
        if not stored_file:
            request_logger.warning("File not found for ingestion")
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
        logger.info(
            "Updated ingestion status to {} (chunks={}, has_error={})",
            status.value,
            stored_file.ingested_chunks,
            bool(stored_file.ingestion_error),
        )

    def _emit_ingestion_status(
        self,
        *,
        user_id: int,
        file_id: int,
        status: IngestionPipelineStatus | str,
        stage: str,
        progress: int,
        chunks: int = 0,
        error: str | None = None,
        ingested_at=None,
        request_logger=None,
    ) -> None:
        status_value = status.value if isinstance(status, IngestionPipelineStatus) else status
        socketio_manager.emit_ingestion_status_sync(
            user_id=user_id,
            payload={
                "file_id": file_id,
                "status": status_value,
                "stage": stage,
                "progress": max(0, min(progress, 100)),
                "chunks": chunks,
                "error": error,
                "updated_at": get_utc_now().isoformat(),
                "ingested_at": ingested_at.isoformat() if ingested_at else None,
            },
        )
        active_logger = request_logger or service_logger.bind(user_id=user_id)
        active_logger.debug(
            "Emitted ingestion status event stage={} status={} progress={}",
            stage,
            status_value,
            progress,
        )

    def _build_chunks(self, text_blocks: list[ExtractedTextBlock]) -> list[IngestionChunk]:
        """Section-aware chunking: headings act as chunk boundaries.

        Each section (heading + body blocks until next heading) becomes one chunk.
        Tables/images are treated as atomic (standalone) chunks.
        Sections exceeding max_section_size are split with overlap as a safety net.
        """
        if not text_blocks:
            return []

        max_section_size = self.chunk_size * 4  # ~4000 chars safety limit

        # --- Helper: finalize a list of blocks into an IngestionChunk ---
        def _finalize_chunk(index: int, blocks: list[ExtractedTextBlock]) -> IngestionChunk:
            seen_bbox_keys: set[tuple] = set()
            bboxes = []
            block_types = []
            for source_block in blocks:
                all_bboxes = source_block.metadata.get("all_bboxes", [])
                if all_bboxes:
                    for bbox_entry in all_bboxes:
                        page_no = bbox_entry.get("page_no")
                        bbox_dict = bbox_entry.get("bbox")
                        if bbox_dict is None:
                            continue
                        key = (page_no, bbox_dict.get("x0"), bbox_dict.get("y0"), bbox_dict.get("x1"), bbox_dict.get("y1"))
                        if key in seen_bbox_keys:
                            continue
                        seen_bbox_keys.add(key)
                        bboxes.append({"page_no": page_no, "bbox": bbox_dict})
                elif source_block.bbox is not None:
                    key = (source_block.page_no, source_block.bbox.get("x0"), source_block.bbox.get("y0"), source_block.bbox.get("x1"), source_block.bbox.get("y1"))
                    if key not in seen_bbox_keys:
                        seen_bbox_keys.add(key)
                        bboxes.append({
                            "page_no": source_block.page_no,
                            "bbox": source_block.bbox,
                        })

            for source_block in blocks:
                bt = source_block.block_type
                if bt and bt not in block_types:
                    block_types.append(bt)

            return IngestionChunk(
                chunk_index=index,  # 1-based index
                text="\n".join(block.text for block in blocks).strip(),
                page_no=next((block.page_no for block in blocks if block.page_no is not None), None),
                bboxes=bboxes,
                block_types=block_types,
            )

        # --- Helper: split an oversized section into sub-chunks ---
        def _split_oversized_section(
            blocks: list[ExtractedTextBlock], chunks: list[IngestionChunk]
        ) -> None:
            """Split a section that exceeds max_section_size using the old
            sliding-window approach, then append resulting chunks."""
            window_blocks: list[ExtractedTextBlock] = []
            window_size = 0

            for block in blocks:
                projected = window_size + len(block.text) + 1
                if window_blocks and projected > self.chunk_size:
                    chunks.append(_finalize_chunk(len(chunks) + 1, window_blocks))

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
                chunks.append(_finalize_chunk(len(chunks) + 1, window_blocks))

        # --- Main logic: group blocks by sections ---
        chunks: list[IngestionChunk] = []
        # Current section accumulator (heading block + body blocks)
        section_blocks: list[ExtractedTextBlock] = []
        section_size = 0

        for block in text_blocks:
            clean_text = block.text.strip()
            if not clean_text:
                continue

            # Normalize block text
            block = ExtractedTextBlock(
                text=clean_text,
                page_no=block.page_no,
                bbox=block.bbox,
                metadata=block.metadata,
                block_type=block.block_type,
                image_data=block.image_data,
            )

            is_heading = block.block_type == "heading"
            is_atomic = block.block_type in ("table", "image")

            # --- Heading: finalize previous section, start new one ---
            if is_heading:
                if section_blocks:
                    if section_size > max_section_size:
                        _split_oversized_section(section_blocks, chunks)
                    else:
                        chunks.append(_finalize_chunk(len(chunks) + 1, section_blocks))
                section_blocks = [block]
                section_size = len(clean_text) + 1
                continue

            # --- Atomic block (table/image): emit as standalone chunk ---
            if is_atomic:
                # First finalize any pending section
                if section_blocks:
                    if section_size > max_section_size:
                        _split_oversized_section(section_blocks, chunks)
                    else:
                        chunks.append(_finalize_chunk(len(chunks) + 1, section_blocks))
                    section_blocks = []
                    section_size = 0

                # Table/image becomes its own chunk
                chunks.append(_finalize_chunk(len(chunks) + 1, [block]))
                continue

            # --- Regular text block: accumulate into current section ---
            section_blocks.append(block)
            section_size += len(clean_text) + 1

        # Finalize any remaining section
        if section_blocks:
            if section_size > max_section_size:
                _split_oversized_section(section_blocks, chunks)
            else:
                chunks.append(_finalize_chunk(len(chunks) + 1, section_blocks))

        return [chunk for chunk in chunks if chunk.text]


    def _embed_chunks(self, chunks: list[IngestionChunk]) -> list[list[float]]:
        if not chunks:
            return []

        api_key = _settings.openai_embedding.api_key
        if not api_key:
            raise InvalidRequestException(
                message=(
                    "Missing embedding API key. Set `AZURE-OPENAI-EMBEDDING-KEY` "
                    "or `OPENAI_API_KEY`."
                )
            )

        if self.embedding_endpoint:
            client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=self.embedding_endpoint,
                api_version=self.embedding_api_version,
                timeout=_settings.openai_embedding.timeout_seconds,
            )
            provider = "azure-openai"
        else:
            client = OpenAI(
                api_key=api_key,
                base_url=_settings.openai_embedding.api_base,
                timeout=_settings.openai_embedding.timeout_seconds,
            )
            provider = "openai"

        service_logger.debug(
            "Generating embeddings for chunk_count={} batch_size={} model={} provider={}",
            len(chunks),
            self.embedding_batch_size,
            self.embedding_model,
            provider,
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
                FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="mime_type", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="bbox", dtype=DataType.VARCHAR, max_length=16384),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=16384),
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
                enable_dynamic_field=True,
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

    @staticmethod
    def _serialize_metadata_payload(
        *,
        user_id: int,
        stored_file: StoredFile,
        chunk: IngestionChunk,
        created_unix: int,
    ) -> str:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "file_id": stored_file.id,
            "file_name": stored_file.name,
            "mime_type": stored_file.mime_type,
            "chunk_index": chunk.chunk_index,
            "page_no": chunk.page_no,
            "block_types": chunk.block_types,
            "created_unix": created_unix,
        }
        serialized = json.dumps(payload, ensure_ascii=False)
        if len(serialized) <= 16000:
            return serialized
        return serialized[:15997] + "..."

    def _upsert_chunks(
        self,
        *,
        user_id: int,
        stored_file: StoredFile,
        chunks: list[IngestionChunk],
        vectors: list[list[float]],
        request_logger,
    ) -> None:
        collection = self._get_milvus_collection()
        delete_expr = f"user_id == {user_id} and file_id == {stored_file.id}"
        try:
            collection.delete(expr=delete_expr)
        except Exception as exc:
            request_logger.warning(
                "Milvus delete before upsert failed for file_id={} user_id={}: {}",
                stored_file.id,
                user_id,
                exc,
            )

        now_unix = int(get_utc_now().timestamp())
        ids = [f"{user_id}:{stored_file.id}:{chunk.chunk_index}" for chunk in chunks]

        column_by_field: dict[str, list[Any]] = {
            "id": ids,
            "user_id": [user_id] * len(chunks),
            "file_id": [stored_file.id] * len(chunks),
            "chunk_index": [chunk.chunk_index for chunk in chunks],
            "page_no": [chunk.page_no if chunk.page_no is not None else -1 for chunk in chunks],
            "text": [chunk.text[:65535] for chunk in chunks],
            "bbox": [self._serialize_bbox_payload(chunk) for chunk in chunks],
            "created_unix": [now_unix] * len(chunks),
            "vector": vectors,
            "file_name": [(stored_file.name or "")[:1024] for _ in chunks],
            "mime_type": [(stored_file.mime_type or "application/octet-stream")[:255] for _ in chunks],
            "metadata_json": [
                self._serialize_metadata_payload(
                    user_id=user_id,
                    stored_file=stored_file,
                    chunk=chunk,
                    created_unix=now_unix,
                )
                for chunk in chunks
            ],
        }

        schema_fields = list(collection.schema.fields)
        missing_required_fields = [
            field.name
            for field in schema_fields
            if not getattr(field, "auto_id", False)
            and not getattr(field, "is_dynamic", False)
            and not str(field.name).startswith("$")
            and field.name not in column_by_field
        ]
        if missing_required_fields:
            raise InvalidRequestException(
                message=(
                    "Milvus collection schema is missing required ingestion columns: "
                    f"{', '.join(missing_required_fields)}"
                )
            )

        rows = [
            column_by_field[field.name]
            for field in schema_fields
            if field.name in column_by_field
        ]

        collection.insert(rows)
        collection.flush()
        request_logger.info(
            "Upserted document vectors into Milvus, chunk_count={}, metadata_fields={}",
            len(chunks),
            [field.name for field in schema_fields if field.name in {"user_id", "file_id", "file_name", "mime_type", "metadata_json"}],
        )

    def _run_ingestion_pipeline(
        self,
        stored_file: StoredFile,
        request_logger,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> tuple[int, str | None]:
        path = Path(stored_file.storage_path)
        request_logger.info("Starting ingestion pipeline for path={}", path)
        if not path.exists():
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)

        if on_progress:
            on_progress("parsing", 20, 0)
        blocks = extract_service.extract_text_blocks(path)
        request_logger.debug("Extracted text blocks, count={}", len(blocks))

        if on_progress:
            on_progress("chunking", 45, 0)
        chunks = self._build_chunks(blocks)
        if not chunks:
            raise InvalidRequestException(message="No text extracted for ingestion")
        request_logger.debug("Built chunks from extracted blocks, chunk_count={}", len(chunks))

        # --- Debug: write extraction + chunking results to JSON for verification ---
        try:
            debug_dir = Path("tmp")
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / f"ingestion_debug_{stored_file.id}.json"

            debug_blocks = []
            for i, block in enumerate(blocks):
                debug_blocks.append({
                    "index": i,
                    "block_type": block.block_type,
                    "docling_label": block.metadata.get("docling_label", ""),
                    "page_no": block.page_no,
                    "text": block.text[:300],
                    "bbox": block.bbox,
                    "all_bboxes": block.metadata.get("all_bboxes", []),
                })

            debug_chunks = []
            for chunk in chunks:
                debug_chunks.append({
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no,
                    "text_preview": chunk.text[:500],
                    "text_length": len(chunk.text),
                    "block_types": chunk.block_types,
                    "bboxes_count": len(chunk.bboxes),
                    "bboxes": chunk.bboxes,
                })

            debug_payload = {
                "file_id": stored_file.id,
                "file_name": stored_file.original_name,
                "total_blocks": len(blocks),
                "total_chunks": len(chunks),
                "blocks": debug_blocks,
                "chunks": debug_chunks,
            }
            debug_file.write_text(
                json.dumps(debug_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            request_logger.info("Wrote ingestion debug JSON to {}", debug_file)
        except Exception as e:
            request_logger.warning("Failed to write debug JSON: {}", e)
        # --- End debug ---

        if on_progress:
            on_progress("indexing", 70, len(chunks))
        vectors = self._embed_chunks(chunks)

        if on_progress:
            on_progress("indexing", 90, len(chunks))
        self._upsert_chunks(
            user_id=stored_file.user_id,
            stored_file=stored_file,
            chunks=chunks,
            vectors=vectors,
            request_logger=request_logger,
        )
        request_logger.info("Ingestion pipeline completed")
        return len(chunks), None

    def ingest_file(
        self,
        request: Request | None,
        db_session: Session,
        user_id: int,
        file_id: int,
    ) -> IngestionRunResponse:
        request_logger = self._get_request_logger(request, user_id)
        stored_file = self._get_user_file(db_session, user_id, file_id, request_logger)
        request_logger.info("Ingestion requested")
        self._set_file_status(
            db_session,
            stored_file,
            IngestionStatus.PROCESSING,
            error=None,
            chunks=0,
            ingested=False,
        )
        self._emit_ingestion_status(
            user_id=user_id,
            file_id=stored_file.id,
            status=IngestionPipelineStatus.PARSING,
            stage="parsing",
            progress=20,
            chunks=0,
            error=None,
            request_logger=request_logger,
        )

        try:
            chunk_count, _ = self._run_ingestion_pipeline(
                stored_file,
                request_logger,
                on_progress=lambda stage, progress, chunks: self._emit_ingestion_status(
                    user_id=user_id,
                    file_id=stored_file.id,
                    status=(
                        IngestionPipelineStatus.PARSING
                        if stage == "parsing"
                        else IngestionPipelineStatus.CHUNKING
                        if stage == "chunking"
                        else IngestionPipelineStatus.INDEXING
                    ),
                    stage=stage,
                    progress=progress,
                    chunks=chunks,
                    error=None,
                    request_logger=request_logger,
                ),
            )
            self._set_file_status(
                db_session,
                stored_file,
                IngestionStatus.COMPLETED,
                error=None,
                chunks=chunk_count,
                ingested=True,
            )
            self._emit_ingestion_status(
                user_id=user_id,
                file_id=stored_file.id,
                status=IngestionPipelineStatus.COMPLETED,
                stage="completed",
                progress=100,
                chunks=chunk_count,
                error=None,
                ingested_at=stored_file.ingested_at,
                request_logger=request_logger,
            )
        except Exception as exc:
            request_logger.exception("Ingestion failed unexpectedly")
            self._set_file_status(
                db_session,
                stored_file,
                IngestionStatus.FAILED,
                error=self._truncate(str(exc), 1000),
                chunks=0,
                ingested=False,
            )
            self._emit_ingestion_status(
                user_id=user_id,
                file_id=stored_file.id,
                status=IngestionPipelineStatus.FAILED,
                stage="failed",
                progress=100,
                chunks=0,
                error=stored_file.ingestion_error,
                request_logger=request_logger,
            )
        else:
            request_logger.info("Ingestion finished successfully with chunks={}", chunk_count)

        return IngestionRunResponse(
            file_id=stored_file.id,
            status=stored_file.ingestion_status,
            chunks=stored_file.ingested_chunks,
            error=stored_file.ingestion_error,
        )

    def ingest_files(
        self,
        request: Request | None,
        db_session: Session,
        user_id: int,
        file_ids: list[int],
    ) -> list[IngestionRunResponse]:
        request_logger = self._get_request_logger(request, user_id)
        request_logger.info(
            "Batch ingestion requested for file_count={}",
            len(file_ids),
        )
        results: list[IngestionRunResponse] = []
        for file_id in file_ids:
            results.append(self.ingest_file(request, db_session, user_id, file_id))
        return results

    def emit_queued_status(
        self,
        *,
        user_id: int,
        file_id: int,
        request: Request | None = None,
    ) -> None:
        request_logger = self._get_request_logger(request, user_id)
        request_logger.debug("Queued ingestion status emitted")
        self._emit_ingestion_status(
            user_id=user_id,
            file_id=file_id,
            status=IngestionPipelineStatus.PENDING,
            stage="pending",
            progress=0,
            chunks=0,
            error=None,
            request_logger=request_logger,
        )

    def ingest_file_by_id(self, user_id: int, file_id: int) -> None:
        db_session = SessionLocal()
        request_logger = self._get_request_logger(user_id=user_id)
        request_logger.info("Background ingestion task started")
        try:
            self.ingest_file(None, db_session, user_id, file_id)
        except Exception:
            request_logger.exception("Background ingestion encountered unexpected failure")
        finally:
            db_session.close()
            request_logger.debug("Background ingestion task finished")

    @staticmethod
    def _decode_json_field(value: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
        if value in (None, ""):
            return None
        if isinstance(value, (dict, list)):
            return value
        if not isinstance(value, str):
            return None
        try:
            decoded = json.loads(value)
        except Exception:
            return None
        if isinstance(decoded, (dict, list)):
            return decoded
        return None

    def list_milvus_collections(self, request: Request | None = None) -> list[dict[str, Any]]:
        request_logger = self._get_request_logger(request)
        try:
            from pymilvus import Collection, connections, utility
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
        collection_names = sorted(utility.list_collections())
        results: list[dict[str, Any]] = []
        for collection_name in collection_names:
            try:
                collection = Collection(collection_name)
                results.append(
                    {
                        "name": collection_name,
                        "num_entities": int(collection.num_entities),
                        "has_index": bool(collection.indexes),
                    }
                )
            except Exception as exc:
                request_logger.warning(
                    "Unable to inspect Milvus collection {}: {}",
                    collection_name,
                    exc,
                )
                results.append(
                    {
                        "name": collection_name,
                        "num_entities": 0,
                        "has_index": False,
                    }
                )

        return results

    def list_chunks(
        self,
        request: Request | None = None,
        *,
        user_id: int,
        file_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], bool]:
        if limit < 1 or limit > 500:
            raise InvalidRequestException(message="`limit` must be between 1 and 500")
        if offset < 0:
            raise InvalidRequestException(message="`offset` must be >= 0")

        collection = self._get_milvus_collection()
        query_expr = f"user_id == {user_id}"
        if file_id is not None:
            query_expr += f" and file_id == {file_id}"

        preferred_output_fields = [
            "id",
            "user_id",
            "file_id",
            "chunk_index",
            "page_no",
            "file_name",
            "mime_type",
            "text",
            "bbox",
            "metadata_json",
            "created_unix",
        ]
        available_fields = {field.name for field in collection.schema.fields}
        output_fields = [
            field_name for field_name in preferred_output_fields if field_name in available_fields
        ]
        if not output_fields:
            raise InvalidRequestException(
                message="Milvus collection does not expose readable fields for chunk listing"
            )

        query_limit = limit + 1
        try:
            rows = collection.query(
                expr=query_expr,
                output_fields=output_fields,
                limit=query_limit,
                offset=offset,
            )
        except TypeError:
            # Older pymilvus versions may not support offset in query.
            rows = collection.query(
                expr=query_expr,
                output_fields=output_fields,
                limit=offset + query_limit,
            )
            rows = rows[offset:]
        except Exception as exc:
            raise InvalidRequestException(
                message=f"Unable to query chunks from Milvus: {exc}"
            ) from exc

        has_more = len(rows) > limit
        selected_rows = rows[:limit]

        chunks: list[dict[str, Any]] = []
        for row in selected_rows:
            bbox_payload = self._decode_json_field(row.get("bbox"))
            metadata_payload = self._decode_json_field(row.get("metadata_json"))
            chunks.append(
                {
                    "id": str(row.get("id", "")),
                    "user_id": int(row.get("user_id", user_id)),
                    "file_id": int(row.get("file_id", file_id or -1)),
                    "chunk_index": int(row.get("chunk_index", 0)),
                    "page_no": (
                        int(row["page_no"]) if row.get("page_no") not in (None, -1) else None
                    ),
                    "file_name": row.get("file_name"),
                    "mime_type": row.get("mime_type"),
                    "text": str(row.get("text", "")),
                    "bbox": bbox_payload,
                    "metadata": metadata_payload,
                    "created_unix": (
                        int(row["created_unix"])
                        if row.get("created_unix") is not None
                        else None
                    ),
                }
            )

        chunks.sort(
            key=lambda item: (
                item["file_id"],
                item["chunk_index"],
            )
        )
        return chunks, has_more

    def get_ingestion_status(
        self,
        request: Request | None,
        db_session: Session,
        user_id: int,
        file_id: int,
    ) -> StoredFile:
        request_logger = self._get_request_logger(request, user_id)
        return self._get_user_file(db_session, user_id, file_id, request_logger)

    def delete_file_vectors(
        self, user_id: int, file_id: int, request: Request | None = None
    ) -> None:
        request_logger = self._get_request_logger(request, user_id)
        try:
            collection = self._get_milvus_collection()
            collection.delete(expr=f"user_id == {user_id} and file_id == {file_id}")
            collection.flush()
            request_logger.info("Deleted vectors from Milvus")
        except Exception as exc:
            request_logger.warning(
                "Skip vector cleanup for file_id={} user_id={} because Milvus is unavailable: {}",
                file_id,
                user_id,
                exc,
            )


data_ingestion_service = DataIngestionService()
