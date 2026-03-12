from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from backend.api.data_ingestion.model import (
    DocumentSuffix,
    DocumentType,
    ExtractedTextBlock,
)
from backend.exceptions.model import InvalidRequestException, NotImplementedException


class DoclingExtractionService:
    """Extract document text with layout metadata (including bounding boxes)."""

    def _get_document_type(self, doc_path: Path) -> DocumentType:
        suffix = doc_path.suffix.lower()
        if suffix in DocumentSuffix.PDF.value:
            return DocumentType.PDF
        if suffix in DocumentSuffix.DOCX.value:
            return DocumentType.DOCX
        if suffix in DocumentSuffix.DOC.value:
            return DocumentType.DOC
        if suffix in DocumentSuffix.EXCEL.value:
            return DocumentType.EXCEL
        if suffix in DocumentSuffix.POWERPOINT.value:
            return DocumentType.POWERPOINT
        if suffix in DocumentSuffix.IMAGE.value:
            return DocumentType.IMAGE
        if suffix in DocumentSuffix.AUDIO.value:
            return DocumentType.AUDIO
        if suffix in DocumentSuffix.VIDEO.value:
            return DocumentType.VIDEO
        raise NotImplementedException(f"Unsupported document type: {suffix}")

    def _preprocess_document(self, doc_path: Path) -> Path:
        if not doc_path.exists():
            raise InvalidRequestException(message=f"Document not found: {doc_path}")

        document_type = self._get_document_type(doc_path)
        if document_type in [DocumentType.AUDIO, DocumentType.VIDEO]:
            raise NotImplementedException(
                f"Docling extraction is not supported for `{document_type.value}` yet."
            )

        return doc_path

    @staticmethod
    def _normalize_bbox(raw_bbox: Any) -> dict[str, float] | None:
        if raw_bbox is None:
            return None

        if isinstance(raw_bbox, dict):
            x0 = raw_bbox.get("x0", raw_bbox.get("l", raw_bbox.get("left")))
            y0 = raw_bbox.get("y0", raw_bbox.get("t", raw_bbox.get("top")))
            x1 = raw_bbox.get("x1", raw_bbox.get("r", raw_bbox.get("right")))
            y1 = raw_bbox.get("y1", raw_bbox.get("b", raw_bbox.get("bottom")))
            if None not in (x0, y0, x1, y1):
                return {
                    "x0": float(x0),
                    "y0": float(y0),
                    "x1": float(x1),
                    "y1": float(y1),
                }
            return None

        for keys in [
            ("l", "t", "r", "b"),
            ("x0", "y0", "x1", "y1"),
            ("left", "top", "right", "bottom"),
        ]:
            values = [getattr(raw_bbox, key, None) for key in keys]
            if None not in values:
                return {
                    "x0": float(values[0]),
                    "y0": float(values[1]),
                    "x1": float(values[2]),
                    "y1": float(values[3]),
                }

        return None

    @staticmethod
    def _extract_item_text(item: Any) -> str:
        for attr_name in ["text", "orig", "raw_text", "content"]:
            value = getattr(item, attr_name, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if isinstance(item, dict):
            for key in ["text", "orig", "raw_text", "content"]:
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    @staticmethod
    def _extract_page_no(raw_prov: Any) -> int | None:
        for key in ["page_no", "page", "page_number"]:
            value = getattr(raw_prov, key, None)
            if value is None and isinstance(raw_prov, dict):
                value = raw_prov.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _extract_provenance(item: Any) -> list[Any]:
        if isinstance(item, dict):
            prov_list = item.get("prov") or item.get("provenance") or []
        else:
            prov_list = getattr(item, "prov", None) or getattr(item, "provenance", None) or []

        if isinstance(prov_list, list):
            return prov_list
        return [prov_list]

    def _convert_with_docling(self, doc_path: Path):
        try:
            from docling.document_converter import DocumentConverter
        except ModuleNotFoundError as exc:
            raise InvalidRequestException(
                message=(
                    "Docling is not installed. Please install `docling` in backend environment."
                )
            ) from exc

        converter = DocumentConverter()
        result = converter.convert(doc_path)
        return result.document

    def extract_text_blocks(self, doc_path: Path) -> list[ExtractedTextBlock]:
        prepared_path = self._preprocess_document(doc_path)
        document = self._convert_with_docling(prepared_path)

        text_blocks: list[ExtractedTextBlock] = []
        iterate_items = getattr(document, "iterate_items", None)

        if callable(iterate_items):
            for node_idx, node in enumerate(iterate_items()):
                item = node[0] if isinstance(node, tuple) else node
                text = self._extract_item_text(item)
                if not text:
                    continue

                provenance_items = self._extract_provenance(item)
                if provenance_items:
                    for provenance in provenance_items:
                        bbox = self._normalize_bbox(
                            provenance.get("bbox")
                            if isinstance(provenance, dict)
                            else getattr(provenance, "bbox", None)
                        )
                        page_no = self._extract_page_no(provenance)
                        text_blocks.append(
                            ExtractedTextBlock(
                                text=text,
                                page_no=page_no,
                                bbox=bbox,
                                metadata={"source": "docling", "node_idx": node_idx},
                            )
                        )
                else:
                    bbox = self._normalize_bbox(
                        item.get("bbox") if isinstance(item, dict) else getattr(item, "bbox", None)
                    )
                    page_no = self._extract_page_no(item)
                    text_blocks.append(
                        ExtractedTextBlock(
                            text=text,
                            page_no=page_no,
                            bbox=bbox,
                            metadata={"source": "docling", "node_idx": node_idx},
                        )
                    )

        if text_blocks:
            return text_blocks

        markdown_text = ""
        export_to_markdown = getattr(document, "export_to_markdown", None)
        if callable(export_to_markdown):
            markdown_text = export_to_markdown() or ""

        if not markdown_text:
            markdown_text = str(document)

        for idx, paragraph in enumerate(markdown_text.split("\n\n")):
            text = paragraph.strip()
            if not text:
                continue
            text_blocks.append(
                ExtractedTextBlock(
                    text=text,
                    page_no=None,
                    bbox=None,
                    metadata={"source": "fallback_markdown", "paragraph_idx": idx},
                )
            )

        logger.info(
            "Extracted {} text blocks from {}",
            len(text_blocks),
            prepared_path,
        )
        return text_blocks


extract_service = DoclingExtractionService()
