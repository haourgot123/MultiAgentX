import os
import logging
from tqdm import tqdm
import uuid
from typing import List, Dict, Any
from app.config.settings import _settings
from app.agent.core.files.process.azure_process import AzureProcessor
from app.agent.core.files.chunks.chunk import DocumentChunking
from app.agent.core.files.db.embedding import Embedding
from app.agent.core.files.db.indexing import Indexing 
from app.agent.utils.files_helper.file_helper import FileHelper
from openai import AsyncAzureOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient
from qdrant_client import AsyncQdrantClient
from azure_ai.factory import AzureAIFactory
from app.databases.vectordb_factory import VectorDBFactory

logger = logging.getLogger(__name__)




class UploadFiles2KnowledgeBase:
    
    def __init__(self, 
        kb_id: str,
        collection_name: str,
    ):
        self.azure_processor = AzureProcessor(kb_id, AzureAIFactory.create_resource("async_chat_azopenai_4_1"), AzureAIFactory.create_resource("document_intelligence"))
        self.chunking = DocumentChunking(kb_id)
        self.embedding = Embedding(AzureAIFactory.create_resource("async_openai_embedding_3_large"))
        self.indexing = Indexing(VectorDBFactory.create_resource("async_qdrant"))
        self.kb_id = kb_id
        self.collection_name = collection_name
        
        
    async def run(
        self, 
        files: List[Dict[str, Any]],
        batch_size: int = _settings.qdrant.qdrant_batch_size
    ):
        sub_folder = str(uuid.uuid4())
        os.makedirs(os.path.join(_settings.process_file.root_download_folder, sub_folder), exist_ok=True)
        os.makedirs(os.path.join(_settings.process_file.root_download_folder, sub_folder, "image"), exist_ok=True)
        files = FileHelper.sort_file_by_size(files)
        for idx, file in enumerate(files):
            try:
                
                logger.info(f"Step 1: Download file {file['file_name']}")
                os.makedirs(os.path.join(_settings.process_file.root_download_folder, sub_folder), exist_ok=True)
                file_content = await FileHelper.download_file(file["file_url"])
                with open(os.path.join(_settings.process_file.root_download_folder, sub_folder, file["file_name"]), "wb") as f:
                    f.write(file_content)
                    
                logger.info(f"Step 2: Process Azure Document Intelligence")
                final_content = await self.azure_processor.run_pipeline(
                    os.path.join(_settings.process_file.root_download_folder, sub_folder, file["file_name"]),
                    os.path.join(_settings.process_file.root_download_folder, sub_folder, "image")
                )
                
                logger.info(f"Step 3: Chunking")
                chunks = self.chunking.run_pipeline(
                    os.path.join(_settings.process_file.root_download_folder, sub_folder, file["file_name"]),
                    final_content,
                    file["file_id"]
                )
                
                logger.info(f"Step 4: Indexing chunks")
                for idx in tqdm(range(0, len(chunks), batch_size), total=len(chunks)//batch_size, desc="Indexing chunks"):
                    batch = chunks[idx:idx + batch_size]
                    batch_embeddings = await self.embedding.embed_documents_batch(batch, batch_size)
                    await self.indexing.index_documents_batch(
                        collection_name=self.collection_name,
                        documents=batch_embeddings,
                        batch_size=batch_size
                    )
                
                logger.info(f"Step 5: Update CallBack for Backend")
                await FileHelper.update_status_callback(
                    kb_id=self.kb_id,
                    file_id=file["file_id"],
                    status="embedded",
                    reason=""
                )
                
                
            except Exception as e:
                logger.error(f"Error processing file {file['file_name']}: {e}")
                await FileHelper.update_status_callback(
                    kb_id=self.kb_id,
                    file_id=file["file_id"],
                    status="failed",
                    reason=str(e)
                )
                continue
        
        # Delete Folder
        if os.path.exists(os.path.join(_settings.process_file.root_download_folder, sub_folder)):
            FileHelper.delete_folder_by_path(
                folder_path=os.path.join(_settings.process_file.root_download_folder, sub_folder)
            )
            