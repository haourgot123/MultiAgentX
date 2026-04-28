from collections import defaultdict
import json

from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk


service_logger = logger.bind(service="rag-combine-context")


def _filter_bbox_json_to_page(bbox_json: str | None, page_no: int | None) -> str:
    if not bbox_json or page_no is None:
        return bbox_json or ""

    try:
        payload = json.loads(bbox_json)
    except (TypeError, ValueError):
        return bbox_json

    if not isinstance(payload, list):
        return bbox_json

    filtered = [
        item
        for item in payload
        if isinstance(item, dict) and item.get("page_no") == page_no
    ]
    if not filtered:
        return bbox_json

    return json.dumps(filtered, ensure_ascii=False)


class CombineContextNode(Runnable):
    """
    Processes retrieved chunks into a structured context string with citation labels.

    Citation format: [file_index.chunk_order], e.g. [1.2] = file #1, chunk #2 within that file.
    Also builds a citation_map for persisting retrieval records to Postgres.
    """

    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_combine_context",
                "message": "Organizing retrieved passages with citations...",
            },
        )

        chunks = state.retrieved_chunks
        if not chunks:
            service_logger.warning("No chunks to combine")
            return {
                "combined_context": "",
                "citation_map": {},
            }

        # Normalize chunks if they are dicts
        normalized_chunks = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                normalized_chunks.append(RetrievedChunk(**chunk))
            else:
                normalized_chunks.append(chunk)

        # Group chunks by file_id, preserving retrieval order inside each file.
        file_groups = defaultdict(list)
        retrieved_file_order = []
        for chunk in normalized_chunks:
            fid = chunk.file_id
            if fid not in retrieved_file_order:
                retrieved_file_order.append(fid)
            file_groups[fid].append(chunk)

        configured_file_ids = list(dict.fromkeys(getattr(state, "file_ids", []) or []))
        file_index_map = {
            fid: idx + 1
            for idx, fid in enumerate(configured_file_ids)
        }
        for fid in retrieved_file_order:
            if fid not in file_index_map:
                file_index_map[fid] = len(file_index_map) + 1

        if configured_file_ids:
            file_order = [
                fid for fid in configured_file_ids if fid in file_groups
            ] + [
                fid for fid in retrieved_file_order if fid not in configured_file_ids
            ]
        else:
            file_order = retrieved_file_order

        # Build context and citation map
        context_parts = []
        citation_map = {}

        for fid in file_order:
            file_idx = file_index_map[fid]
            # Sort chunks within each file by page_no then chunk_index
            # so that adjacent chunks remain contiguous in the context
            sorted_chunks = sorted(
                file_groups[fid],
                key=lambda c: (c.page_no if c.page_no is not None else 0, c.chunk_index),
            )
            for chunk in sorted_chunks:
                # Use the original chunk_index from ingestion (1-based, document order)
                citation_label = f"{file_idx}.{chunk.chunk_index}"

                # Build formatted context block
                header = f"[{citation_label}]"
                if chunk.file_name:
                    header += f" File: {chunk.file_name}"
                if chunk.page_no and chunk.page_no > 0:
                    header += f", Page {chunk.page_no}"
                if chunk.score > 0:
                    header += f" (score: {chunk.score:.2f})"

                context_parts.append(f"{header}\n{chunk.text}")

                # Build citation map entry for retrieval records
                citation_map[citation_label] = {
                    "chunk_id": chunk.chunk_id,
                    "file_id": chunk.file_id,
                    "file_name": chunk.file_name or "",
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no,
                    "bbox_json": _filter_bbox_json_to_page(
                        chunk.bbox_json,
                        chunk.page_no,
                    ),
                    "chunk_text": chunk.text[:2000],  # Truncate for storage
                    "relevance_score": str(round(chunk.score, 4)),
                }

        combined_context = "\n\n---\n\n".join(context_parts)

        service_logger.info(
            f"Combined {len(normalized_chunks)} chunks across {len(file_order)} file(s) "
            f"into {len(citation_map)} cited passages"
        )

        return {
            "combined_context": combined_context,
            "citation_map": citation_map,
        }
