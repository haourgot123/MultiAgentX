from pathlib import Path
from typing import List, Literal

import torch
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
    TableStructureOptions,
    TesseractCliOcrOptions,
    ThreadedPdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

from backend.api.data_ingestion.model import DocumentSuffix, DocumentType
from backend.exceptions.model import NotImplementedException


class DoclingExtractionService:
    """Service for extracting text and data from various document formats using Docling."""

    def _get_document_type(self, doc_path: Path) -> DocumentType:
        """
        Get the document type from the file extension.
        Args:
            doc_path: Path to the document.
        Returns:
            DocumentType: The document type.
        """
        if doc_path.suffix.lower() in DocumentSuffix.PDF.value:
            return DocumentType.PDF
        elif doc_path.suffix.lower() in DocumentSuffix.DOCX.value:
            return DocumentType.DOCX
        elif doc_path.suffix.lower() in DocumentSuffix.DOC.value:
            return DocumentType.DOC
        elif doc_path.suffix.lower() in DocumentSuffix.EXCEL.value:
            return DocumentType.EXCEL
        elif doc_path.suffix.lower() in DocumentSuffix.POWERPOINT.value:
            return DocumentType.POWERPOINT
        elif doc_path.suffix.lower() in DocumentSuffix.IMAGE.value:
            return DocumentType.IMAGE
        elif doc_path.suffix.lower() in DocumentSuffix.AUDIO.value:
            return DocumentType.AUDIO
        elif doc_path.suffix.lower() in DocumentSuffix.VIDEO.value:
            return DocumentType.VIDEO
        else:
            raise NotImplementedException(
                f"Unsupported document type: {doc_path.suffix.lower()}"
            )

    def _preprocess_document(self, doc_path: Path) -> Path:
        """
        Preprocess the document to make it compatible with Docling.
        Args:
            doc_path: Path to the document.
        Returns:
            Path: The path to the preprocessed document.
        """
        document_type = self._get_document_type(doc_path)
        if document_type in [
            DocumentType.DOCX,
            DocumentType.DOC,
            DocumentType.EXCEL,
            DocumentType.POWERPOINT,
            DocumentType.IMAGE,
        ]:
            # TODO: Implement conversion to PDF
            return doc_path
        else:
            return doc_path

    def _get_device_type(self) -> str:
        """
        Get the device type.
        Returns:
            str: The device type.
        """

        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _get_vllm_picture_annotation_with_vlm(
        self,
        model: str,
        seed: int = 42,
        timeout: int = 120,
        max_completion_tokens: int = 512,
        host: str = "localhost",
        port: int = 8000,
        prompt: str = "Describe the image in three sentences. Be consise and accurate.",
    ) -> PictureDescriptionApiOptions:
        """
        Get the picture annotation with VLM using VLLM.
        Args:
            model: The model to use.
            seed: The seed to use.
            timeout: The timeout to use.
            max_completion_tokens: The maximum completion tokens to use.
            host: The host to use.
            port: The port to use.
            prompt: The prompt to use.
        Returns:
            option: DoclingOption: The Docling option.
        """

        options = PictureDescriptionApiOptions(
            url=f"http://{host}:{port}/v1/chat/completions",
            params=dict(
                model=model,
                seed=seed,
                max_completion_tokens=max_completion_tokens,
            ),
            prompt=prompt,
            timeout=timeout,
        )
        return options

    def _get_lms_picture_annotation_with_vlm(
        self,
        model: str,
        seed: int = 42,
        timeout: int = 120,
        max_completion_tokens: int = 512,
        host: str = "localhost",
        port: int = 1234,
        prompt: str = "Describe the image in three sentences. Be consise and accurate.",
    ) -> PictureDescriptionApiOptions:
        """
        Get the picture annotation with VLM using LMS.
        Args:
            model: The model to use.
            seed: The seed to use.
            timeout: The timeout to use.
            max_completion_tokens: The maximum completion tokens to use.
            host: The host to use.
            port: The port to use.
            prompt: The prompt to use.
        Returns:
            option: DoclingOption: The Docling option.
        """
        options = PictureDescriptionApiOptions(
            url=f"http://{host}:{port}/v1/chat/completions",
            params=dict(
                model=model,
                seed=seed,
                max_completion_tokens=max_completion_tokens,
            ),
            prompt=prompt,
            timeout=timeout,
        )
        return options

    def _get_accelerator_config(
        self,
        num_threads: int = 4,
    ) -> AcceleratorOptions:
        """
        Get the CUDA configuration.
        Args:
            num_threads: The number of threads to use.
        Returns:
            AcceleratorOptions: The CUDA configuration.
        """

        device_type = self._get_device_type()
        return AcceleratorOptions(
            num_threads=num_threads,
            device=device_type,
        )

    def _get_standard_converter(
        self,
        do_ocr: bool = True,
        force_full_page_ocr: bool = True,
        do_table_structure: bool = True,
        do_cell_matching: bool = True,
        vlm_framework: Literal["vllm", "lms"] = "vllm",
        vlm_model: str = None,
    ) -> DocumentConverter:
        """
        Get the standard converter.
        Args:
            do_ocr: Whether to do OCR.
            force_full_page_ocr: Whether to force full page OCR.
            do_table_structure: Whether to do table structure.
            do_cell_matching: Whether to do cell matching.
            vlm_framework: The framework to use for picture description.
            vlm_model: The model to use for picture description.
        Returns:
            DocumentConverter: The standard converter.
        """

        ocr_options = TesseractCliOcrOptions(lang=["auto"])
        pipeline_options = PdfPipelineOptions(
            do_ocr=do_ocr,
            force_full_page_ocr=force_full_page_ocr,
            ocr_options=ocr_options,
            do_table_structure=do_table_structure,
            table_structure_options=TableStructureOptions(
                do_cell_matching=do_cell_matching,
            ),
        )

        if vlm_model is not None:
            if vlm_framework == "vllm":
                picture_description_options = (
                    self._get_vllm_picture_annotation_with_vlm(vlm_model)
                )
            elif vlm_framework == "lms":
                picture_description_options = self._get_lms_picture_annotation_with_vlm(
                    vlm_model
                )

            # Set the picture description options
            pipeline_options.picture_description_options = picture_description_options

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )
        return converter

    def _get_accelerator_converter(
        self,
        do_ocr: bool = True,
        force_full_page_ocr: bool = True,
        do_table_structure: bool = True,
        do_cell_matching: bool = True,
        num_threads: int = 4,
        ocr_batch_size: int = 4,
        layout_batch_size: int = 64,
        table_batch_size: int = 4,
        vlm_framework: Literal["vllm", "lms"] = "vllm",
        vlm_model: str = None,
    ) -> DocumentConverter:
        """
        Get the accelerator converter.
        Args:
            device: The device to use.
            num_threads: The number of threads to use.
            ocr_batch_size: The batch size for OCR.
            layout_batch_size: The batch size for layout.
            table_batch_size: The batch size for table structure.
            do_ocr: Whether to do OCR.
            force_full_page_ocr: Whether to force full page OCR.
            do_table_structure: Whether to do table structure.
            do_cell_matching: Whether to do cell matching.
            vlm_framework: The framework to use for picture description.
            vlm_model: The model to use for picture description.
        Returns:
            DocumentConverter: The accelerator converter.
        """

        ocr_options = TesseractCliOcrOptions(lang=["auto"])
        accelerator_config = self._get_accelerator_config(num_threads=num_threads)
        pipeline_options = ThreadedPdfPipelineOptions(
            accelerator_options=accelerator_config,
            ocr_batch_size=ocr_batch_size,
            layout_batch_size=layout_batch_size,
            table_batch_size=table_batch_size,
            force_full_page_ocr=force_full_page_ocr,
            do_ocr=do_ocr,
            do_table_structure=do_table_structure,
            table_structure_options=TableStructureOptions(
                do_cell_matching=do_cell_matching,
            ),
            ocr_options=ocr_options,
        )

        if vlm_model is not None:
            if vlm_framework == "vllm":
                picture_description_options = (
                    self._get_vllm_picture_annotation_with_vlm(vlm_model)
                )
            elif vlm_framework == "lms":
                picture_description_options = self._get_lms_picture_annotation_with_vlm(
                    vlm_model
                )

            # Set the picture description options
            pipeline_options.picture_description_options = picture_description_options

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        return converter

    def _extract_document(
        self,
        doc_path: Path,
        output_folder: Path = Path("temp"),
        is_accelerator: bool = False,
        ocr_batch_size: int = 4,
        layout_batch_size: int = 64,
        table_batch_size: int = 4,
        do_ocr: bool = True,
        do_table_structure: bool = True,
        do_cell_matching: bool = True,
        force_full_page_ocr: bool = True,
        num_threads: int = 4,
        vlm_framework: Literal["vllm", "lms"] = "vllm",
        vlm_model: str = None,
    ):
        """
        Extract the text from the document.
        Args:
            doc_path: Path to the document.
            output_folder: Path to the output folder.
            is_accelerator: Whether to use accelerator.
            ocr_batch_size: The batch size for OCR.
            layout_batch_size: The batch size for layout.
            table_batch_size: The batch size for table structure.
            do_ocr: Whether to do OCR.
            do_table_structure: Whether to do table structure.
            do_cell_matching: Whether to do cell matching.
            force_full_page_ocr: Whether to force full page OCR.
            num_threads: The number of threads to use.
            vlm_framework: The framework to use for picture description.
            vlm_model: The model to use for picture description.s
        Returns:
            str: The text from the document.
        """
        # Check if the document exists
        if not doc_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_path}")

        # Check if the output folder exists
        if not output_folder.exists():
            output_folder.mkdir(parents=True, exist_ok=True)

        if is_accelerator:
            converter = self._get_accelerator_converter(
                ocr_batch_size=ocr_batch_size,
                layout_batch_size=layout_batch_size,
                table_batch_size=table_batch_size,
                do_ocr=do_ocr,
                do_table_structure=do_table_structure,
                do_cell_matching=do_cell_matching,
                vlm_framework=vlm_framework,
                vlm_model=vlm_model,
            )
        else:
            converter = self._get_standard_converter(
                do_ocr=do_ocr,
                force_full_page_ocr=force_full_page_ocr,
                do_table_structure=do_table_structure,
                do_cell_matching=do_cell_matching,
                num_threads=num_threads,
                vlm_framework=vlm_framework,
                vlm_model=vlm_model,
            )

        doc = converter.convert(doc_path).document
        return doc
