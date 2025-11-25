from .celery_config import celery_app
from loguru import logger
from typing import List, Dict, Any       
import asyncio

@celery_app.task(bind=True, name='process_file', max_retries=0)
def process_file(
    self,
    kb_id: str, 
    collection_name: str,
    files: List[Dict[str, Any]]
):
    try:
        
        from .run import UploadFiles2KnowledgeBase
        upload_files_2_knowledge_base = UploadFiles2KnowledgeBase(
            kb_id, 
            collection_name
        )
        asyncio.run(upload_files_2_knowledge_base.run(files))
        logger.info(f"Successfully completed pipeline processing for KB: {kb_id} with {len(files)} files")
        
    except Exception as e:
        logger.error(f"Processing file failed for KB {kb_id}: {e}")
        raise

            
        




