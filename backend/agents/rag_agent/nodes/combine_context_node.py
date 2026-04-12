from collections import defaultdict

from langchain_core.runnables import Runnable
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk


service_logger = logger.bind(service="rag-combine-context")


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

        # Group chunks by file_id, preserving order
        file_groups = defaultdict(list)
        file_order = []
        for chunk in normalized_chunks:
            fid = chunk.file_id
            if fid not in file_order:
                file_order.append(fid)
            file_groups[fid].append(chunk)

        # Assign file_index (1-based)
        file_index_map = {fid: idx + 1 for idx, fid in enumerate(file_order)}

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
                    "bbox_json": chunk.bbox_json or "",
                    "chunk_text": chunk.text[:2000],  # Truncate for storage
                    "relevance_score": str(round(chunk.score, 4)),
                }

        combined_context = "\n\n---\n\n".join(context_parts)

        service_logger.info(
            f"Combined {len(normalized_chunks)} chunks across {len(file_order)} file(s) "
            f"into {len(citation_map)} cited passages"
        )

        dispatch_custom_event(
            "status",
            {
                "step": "rag_combine_context",
                "message": f"Organized {len(citation_map)} passages with citations from {len(file_order)} file(s).",
            },
        )

        return {
            "combined_context": combined_context,
            "citation_map": citation_map,
        }
