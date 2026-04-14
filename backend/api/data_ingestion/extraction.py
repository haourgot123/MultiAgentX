from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from loguru import logger

from backend.api.data_ingestion.model import (
    DocumentSuffix,
    DocumentType,
    ExtractedTextBlock,
)
from backend.api.data_ingestion.summarizer import ingestion_summarizer
from backend.exceptions.model import InvalidRequestException, NotImplementedException


class DoclingExtractionService:
    """Extract document text with layout metadata (including bounding boxes).

    Handles TextItem, TableItem, and PictureItem from Docling:
    - TextItem: regular paragraphs, headings, etc.
    - TableItem: exports to markdown, merges caption text, marks as block_type="table"
    - PictureItem: extracts image data + caption/description, marks as block_type="image"

    Captions that are referenced by TableItem/PictureItem are merged into their
    parent blocks so they are not duplicated as standalone text blocks.
    """

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
            y_top = raw_bbox.get("y0", raw_bbox.get("t", raw_bbox.get("top")))
            x1 = raw_bbox.get("x1", raw_bbox.get("r", raw_bbox.get("right")))
            y_bottom = raw_bbox.get("y1", raw_bbox.get("b", raw_bbox.get("bottom")))
            if None not in (x0, y_top, x1, y_bottom):
                fx0, fx1 = float(x0), float(x1)
                fy0, fy1 = float(y_top), float(y_bottom)
                if fx0 > fx1:
                    fx0, fx1 = fx1, fx0
                if fy0 > fy1:
                    fy0, fy1 = fy1, fy0
                return {
                    "x0": fx0,
                    "y0": fy0,
                    "x1": fx1,
                    "y1": fy1,
                }
            return None

        for keys in [
            ("l", "t", "r", "b"),
            ("x0", "y0", "x1", "y1"),
            ("left", "top", "right", "bottom"),
        ]:
            values = [getattr(raw_bbox, key, None) for key in keys]
            if None not in values:
                fx0, fy_top, fx1, fy_bottom = (
                    float(values[0]),
                    float(values[1]),
                    float(values[2]),
                    float(values[3]),
                )
                if fx0 > fx1:
                    fx0, fx1 = fx1, fx0
                if fy_top > fy_bottom:
                    fy_top, fy_bottom = fy_bottom, fy_top
                return {
                    "x0": fx0,
                    "y0": fy_top,
                    "x1": fx1,
                    "y1": fy_bottom,
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

    @staticmethod
    def _resolve_caption_text(item: Any, document: Any) -> str:
        caption_refs = getattr(item, "captions", None) or []
        if not caption_refs:
            return ""
        caption_texts: list[str] = []
        for ref in caption_refs:
            cref = getattr(ref, "cref", None) or (ref if isinstance(ref, str) else None)
            if cref is None:
                continue
            try:
                resolved = document.resolve(cref) if hasattr(document, "resolve") else None
                if resolved is not None:
                    text = DoclingExtractionService._extract_item_text(resolved)
                    if text:
                        caption_texts.append(text)
            except Exception:
                pass
        return " ".join(caption_texts).strip()

    @staticmethod
    def _resolve_description(item: Any) -> str:
        meta = getattr(item, "meta", None)
        if meta is None:
            return ""
        description_field = getattr(meta, "description", None)
        if description_field is None:
            return ""
        if isinstance(description_field, str):
            return description_field.strip()
        text = getattr(description_field, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return ""

    @staticmethod
    def _extract_image_data(item: Any) -> str | None:
        image_ref = getattr(item, "image", None)
        if image_ref is None:
            return None

        pil_image = getattr(image_ref, "pil_image", None)
        if callable(pil_image):
            try:
                pil_image = pil_image()
            except Exception:
                pil_image = None

        if pil_image is not None:
            try:
                import io

                from PIL import Image as PILImage

                if isinstance(pil_image, PILImage.Image):
                    buf = io.BytesIO()
                    pil_image.save(buf, format="PNG")
                    return base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception:
                pass

        uri = getattr(image_ref, "uri", None)
        if uri is not None:
            uri_str = str(uri)
            if uri_str.startswith("data:"):
                base64_part = uri_str.split(",", 1)
                if len(base64_part) == 2:
                    return base64_part[1]

        return None

    @staticmethod
    def _extract_provenance_bboxes(item: Any) -> list[dict[str, Any]]:
        provenance_items = DoclingExtractionService._extract_provenance(item)
        bboxes: list[dict[str, Any]] = []
        for prov in provenance_items:
            raw_bbox = (
                prov.get("bbox") if isinstance(prov, dict) else getattr(prov, "bbox", None)
            )
            normalized = DoclingExtractionService._normalize_bbox(raw_bbox)
            page_no = DoclingExtractionService._extract_page_no(prov)
            if normalized is not None:
                bboxes.append({"page_no": page_no, "bbox": normalized})
        return bboxes

    def _collect_caption_refs(self, document: Any) -> set[str]:
        caption_refs: set[str] = set()
        for attr_name in ["tables", "pictures"]:
            items = getattr(document, attr_name, None)
            if items is None:
                continue
            for item in items:
                captions = getattr(item, "captions", None) or []
                for cap_ref in captions:
                    cref = getattr(cap_ref, "cref", None) or (
                        cap_ref if isinstance(cap_ref, str) else None
                    )
                    if cref is not None:
                        caption_refs.add(cref)
        return caption_refs

    def _extract_text_block(self, item: Any, node_idx: int) -> ExtractedTextBlock | None:
        text = self._extract_item_text(item)
        if not text:
            return None

        provenance_items = self._extract_provenance(item)
        if provenance_items:
            all_bboxes: list[dict[str, Any]] = []
            for prov in provenance_items:
                bbox = self._normalize_bbox(
                    prov.get("bbox")
                    if isinstance(prov, dict)
                    else getattr(prov, "bbox", None)
                )
                page_no = self._extract_page_no(prov)
                if bbox is not None:
                    all_bboxes.append({"page_no": page_no, "bbox": bbox})

            representative_page_no = all_bboxes[0].get("page_no") if all_bboxes else None
            representative_bbox = all_bboxes[0].get("bbox") if all_bboxes else None

            return ExtractedTextBlock(
                text=text,
                page_no=representative_page_no,
                bbox=representative_bbox,
                metadata={
                    "source": "docling",
                    "node_idx": node_idx,
                    "block_type": "text",
                    "all_bboxes": all_bboxes,
                },
                block_type="text",
            )
        else:
            bbox = self._normalize_bbox(
                item.get("bbox") if isinstance(item, dict) else getattr(item, "bbox", None)
            )
            page_no = self._extract_page_no(item)
            all_bboxes = [{"page_no": page_no, "bbox": bbox}] if bbox is not None else []
            return ExtractedTextBlock(
                text=text,
                page_no=page_no,
                bbox=bbox,
                metadata={
                    "source": "docling",
                    "node_idx": node_idx,
                    "block_type": "text",
                    "all_bboxes": all_bboxes,
                },
                block_type="text",
            )

    def _extract_table_block(
        self, item: Any, document: Any, node_idx: int
    ) -> ExtractedTextBlock | None:
        table_text = ""
        export_to_markdown = getattr(item, "export_to_markdown", None)
        if callable(export_to_markdown):
            try:
                table_text = export_to_markdown(document)
                if table_text:
                    table_text = table_text.strip()
            except Exception:
                table_text = ""

        if not table_text:
            data = getattr(item, "data", None)
            if data is not None:
                table_cells = getattr(data, "table_cells", None) or []
                cell_texts = []
                for cell in table_cells:
                    cell_text = getattr(cell, "text", None)
                    if cell_text and cell_text.strip():
                        cell_texts.append(cell_text.strip())
                if cell_texts:
                    table_text = " | ".join(cell_texts)

        caption_text = self._resolve_caption_text(item, document)
        if caption_text and table_text:
            full_text = f"[Table Caption: {caption_text}]\n{table_text}"
        elif caption_text:
            full_text = f"[Table Caption: {caption_text}]"
        else:
            full_text = table_text

        if not full_text.strip():
            return None

        prov_bboxes = self._extract_provenance_bboxes(item)
        representative_page_no = prov_bboxes[0].get("page_no") if prov_bboxes else None
        representative_bbox = prov_bboxes[0].get("bbox") if prov_bboxes else None

        return ExtractedTextBlock(
            text=full_text,
            page_no=representative_page_no,
            bbox=representative_bbox,
            metadata={
                "source": "docling",
                "node_idx": node_idx,
                "block_type": "table",
                "all_bboxes": prov_bboxes,
            },
            block_type="table",
        )

    def _extract_picture_block(
        self, item: Any, document: Any, node_idx: int
    ) -> ExtractedTextBlock | None:
        image_data = self._extract_image_data(item)
        description = self._resolve_description(item)
        caption_text = self._resolve_caption_text(item, document)

        parts: list[str] = []
        if caption_text:
            parts.append(f"[Image Caption: {caption_text}]")
        if description:
            parts.append(f"[Image Description: {description}]")

        if not parts and not image_data:
            prov_bboxes = self._extract_provenance_bboxes(item)
            if not prov_bboxes:
                return None

        full_text = "\n".join(parts) if parts else "[Image]"

        prov_bboxes = self._extract_provenance_bboxes(item)
        representative_page_no = prov_bboxes[0].get("page_no") if prov_bboxes else None
        representative_bbox = prov_bboxes[0].get("bbox") if prov_bboxes else None

        return ExtractedTextBlock(
            text=full_text,
            page_no=representative_page_no,
            bbox=representative_bbox,
            metadata={
                "source": "docling",
                "node_idx": node_idx,
                "block_type": "image",
                "all_bboxes": prov_bboxes,
            },
            block_type="image",
            image_data=image_data,
        )

    def _convert_with_docling(self, doc_path: Path):
        try:
            from docling.document_converter import DocumentConverter
        except ModuleNotFoundError as exc:
            raise InvalidRequestException(
                message=(
                    "Docling is not installed. Please install `docling` in backend environment."
                )
            ) from exc

        try:
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption

            pipeline_options = PdfPipelineOptions()
            pipeline_options.generate_picture_images = True
            converter = DocumentConverter(
                format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
            )
        except (ImportError, Exception):
            # Fallback: use default converter if options are unavailable
            converter = DocumentConverter()

        result = converter.convert(doc_path)
        return result.document

    def extract_text_blocks(self, doc_path: Path) -> list[ExtractedTextBlock]:
        prepared_path = self._preprocess_document(doc_path)
        document = self._convert_with_docling(prepared_path)

        text_blocks: list[ExtractedTextBlock] = []
        caption_refs = self._collect_caption_refs(document)
        iterate_items = getattr(document, "iterate_items", None)

        if callable(iterate_items):
            for node_idx, node in enumerate(iterate_items()):
                item = node[0] if isinstance(node, tuple) else node

                item_self_ref = getattr(item, "self_ref", None)
                if item_self_ref and item_self_ref in caption_refs:
                    continue

                item_label = getattr(item, "label", None)
                label_str = str(item_label).lower() if item_label is not None else ""
                # Docling label may be an enum (e.g., DocItemLabel.SECTION_HEADER)
                # Extract just the value name for matching
                if "." in label_str:
                    label_str = label_str.rsplit(".", 1)[-1]

                if label_str in ("table", "document_index"):
                    block = self._extract_table_block(item, document, node_idx)
                    if block:
                        text_blocks.append(block)
                    continue

                if label_str in ("picture", "chart"):
                    block = self._extract_picture_block(item, document, node_idx)
                    if block:
                        text_blocks.append(block)
                    continue

                # Detect headings for section-based chunking
                if label_str in ("title", "section_header"):
                    block = self._extract_text_block(item, node_idx)
                    if block:
                        block = ExtractedTextBlock(
                            text=block.text,
                            page_no=block.page_no,
                            bbox=block.bbox,
                            metadata={**block.metadata, "block_type": "heading", "docling_label": label_str},
                            block_type="heading",
                        )
                        text_blocks.append(block)
                    continue

                if hasattr(item, "data") and hasattr(item, "captions"):
                    try:
                        from docling_core.types.doc.document import TableItem as _TI

                        if isinstance(item, _TI):
                            block = self._extract_table_block(item, document, node_idx)
                            if block:
                                text_blocks.append(block)
                            continue
                    except ImportError:
                        pass

                    try:
                        from docling_core.types.doc.document import PictureItem as _PI

                        if isinstance(item, _PI):
                            block = self._extract_picture_block(item, document, node_idx)
                            if block:
                                text_blocks.append(block)
                            continue
                    except ImportError:
                        pass

                block = self._extract_text_block(item, node_idx)
                if block:
                    # Save the docling label in metadata for debugging
                    block = ExtractedTextBlock(
                        text=block.text,
                        page_no=block.page_no,
                        bbox=block.bbox,
                        metadata={**block.metadata, "docling_label": label_str},
                        block_type=block.block_type,
                        image_data=block.image_data,
                    )
                    text_blocks.append(block)

        if text_blocks:
            text_blocks = self._add_gpt_summaries(text_blocks)
            logger.info(
                "Extracted {} text blocks (with GPT summaries) from {}",
                len(text_blocks),
                prepared_path,
            )
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
                    block_type="text",
                )
            )

        logger.info(
            "Extracted {} text blocks (fallback markdown) from {}",
            len(text_blocks),
            prepared_path,
        )
        return text_blocks

    def _add_gpt_summaries(
        self, blocks: list[ExtractedTextBlock]
    ) -> list[ExtractedTextBlock]:
        summarizable_blocks: list[dict[str, Any]] = []
        summarizable_indices: list[int] = []

        for idx, block in enumerate(blocks):
            if block.block_type in ("table", "image"):
                summarizable_blocks.append(
                    {
                        "block_type": block.block_type,
                        "text": block.text,
                        "image_data": block.image_data,
                    }
                )
                summarizable_indices.append(idx)

        if not summarizable_blocks:
            return blocks

        summaries = ingestion_summarizer.summarize_blocks_sync(summarizable_blocks)

        for i, block_idx in enumerate(summarizable_indices):
            summary = summaries[i] if i < len(summaries) else None
            if summary:
                original_text = blocks[block_idx].text
                block_type_label = (
                    "Table" if blocks[block_idx].block_type == "table" else "Image"
                )
                blocks[block_idx] = ExtractedTextBlock(
                    text=f"[{block_type_label} Summary: {summary}]\n{original_text}",
                    page_no=blocks[block_idx].page_no,
                    bbox=blocks[block_idx].bbox,
                    metadata=blocks[block_idx].metadata,
                    block_type=blocks[block_idx].block_type,
                    image_data=blocks[block_idx].image_data,
                )

        return blocks


extract_service = DoclingExtractionService()