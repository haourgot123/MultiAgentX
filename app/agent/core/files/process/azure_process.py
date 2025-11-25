import os
import asyncio
import logging
from typing import Any
from azure.ai.documentintelligence.models import AnalyzeResult, ContentFormat
from .azure_process_tables import identify_and_merge_cross_page_tables, describe_tables
from .azure_process_images import describe_figures
from app.agent.utils.files_helper.process_file_helper import ProcessTableHelper, ProcessImageHelper
from app.agent.utils.tools_helper.s3 import S3Service
from app.agent.utils.tools_helper.model import S3ServiceUploadFileWithFilePathModel
from app.config.settings import _settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureProcessor:

    def __init__(self, 
        kb_id: str,
        azure_chat_client: Any,
        azure_document_intelligence_client: Any,
    ):
        self.s3_service = S3Service()
        self.azure_chat_client = azure_chat_client
        self.azure_document_intelligence_client = azure_document_intelligence_client
        self.kb_id = kb_id

    async def run_pipeline(
        self, 
        input_file_path: str, 
        img_output_folder: str,
    ) -> str:            
        with open(input_file_path, "rb") as f:
            poller = self.azure_document_intelligence_client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=f,
                content_type="application/octet-stream",
                output_content_format=ContentFormat.MARKDOWN,
            )
        result: AnalyzeResult = poller.result()
        logger.info(f"Analyze document result successfully")

        img_descriptions, img_paths = await describe_figures(
            self.azure_chat_client,
            input_file_path, 
            img_output_folder, 
            result
        )
        logger.info(f"Describe figures successfully")
        
        for img_path in img_paths:
            if os.path.exists(img_path):
                file_name = os.path.basename(img_path)
                s3_key = f"{_settings.s3.prefix}/{self.kb_id}/{file_name}"
                await asyncio.to_thread(
                    self.s3_service.upload_file_path, 
                    S3ServiceUploadFileWithFilePathModel(key=s3_key, file_path=img_path)
                )

        optimized_md_content = identify_and_merge_cross_page_tables(result)
        table_descriptions = await describe_tables(self.azure_chat_client, optimized_md_content)
        optimized_md_content = ProcessTableHelper.insert_table_description(
            optimized_md_content, table_descriptions
        )
        # Update figure description
        optimized_md_content = ProcessImageHelper.update_figure_description_with_regex(
            optimized_md_content, img_descriptions, img_paths
        )

        return optimized_md_content

    
        
        
        
        
    
        
        
    
    
    
    